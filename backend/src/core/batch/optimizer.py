"""
批量操作优化器

提供批量数据库操作、批量API处理、异步任务队列等功能
"""
import asyncio
import time
import uuid
import structlog
from typing import Any, Dict, List, Optional, Union, Callable, TypeVar, Generic
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from ..database.optimized_pool import get_db_pool
from ..cache.enhanced_cache import get_multi_cache

logger = structlog.get_logger(__name__)

T = TypeVar('T')


class BatchOperationStatus(Enum):
    """批量操作状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class BatchOperationType(Enum):
    """批量操作类型"""
    DATABASE_INSERT = "database_insert"
    DATABASE_UPDATE = "database_update"
    DATABASE_DELETE = "database_delete"
    API_REQUEST = "api_request"
    CACHE_OPERATION = "cache_operation"
    CUSTOM = "custom"


@dataclass
class BatchTask:
    """批量任务"""
    task_id: str
    operation_type: BatchOperationType
    operation_data: Any
    status: BatchOperationStatus = BatchOperationStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[Any] = None
    error: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    dependencies: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'task_id': self.task_id,
            'operation_type': self.operation_type.value,
            'status': self.status.value,
            'created_at': self.created_at.isoformat(),
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'result': self.result,
            'error': self.error,
            'retry_count': self.retry_count,
            'max_retries': self.max_retries,
            'dependencies': self.dependencies
        }


@dataclass
class BatchJob:
    """批量作业"""
    job_id: str
    name: str
    description: str
    tasks: List[BatchTask] = field(default_factory=list)
    status: BatchOperationStatus = BatchOperationStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    config: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'job_id': self.job_id,
            'name': self.name,
            'description': self.description,
            'total_tasks': len(self.tasks),
            'completed_tasks': len([t for t in self.tasks if t.status == BatchOperationStatus.COMPLETED]),
            'failed_tasks': len([t for t in self.tasks if t.status == BatchOperationStatus.FAILED]),
            'status': self.status.value,
            'created_at': self.created_at.isoformat(),
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'config': self.config,
            'tasks': [task.to_dict() for task in self.tasks]
        }


class DatabaseBatchProcessor:
    """数据库批量操作处理器"""

    def __init__(self, batch_size: int = 1000, chunk_size: int = 100):
        self.batch_size = batch_size
        self.chunk_size = chunk_size

    async def batch_insert(self,
                         table_name: str,
                         data_list: List[Dict[str, Any]],
                         conflict_strategy: str = "ignore") -> Dict[str, Any]:
        """批量插入数据"""
        start_time = time.time()
        total_count = len(data_list)

        if not data_list:
            return {
                'total_count': 0,
                'inserted_count': 0,
                'duration_ms': 0,
                'chunks': 0
            }

        db_pool = get_db_pool()
        inserted_count = 0
        chunks_processed = 0

        try:
            # 将数据分块处理
            for i in range(0, total_count, self.chunk_size):
                chunk = data_list[i:i + self.chunk_size]

                async with db_pool.get_session() as session:
                    # 构建批量插入SQL
                    columns = list(chunk[0].keys())
                    columns_str = ', '.join(columns)
                    values_str = ', '.join([f":{col}" for col in columns])

                    if conflict_strategy == "ignore":
                        sql = f"""
                        INSERT INTO {table_name} ({columns_str})
                        VALUES {values_str}
                        ON CONFLICT DO NOTHING
                        """
                    elif conflict_strategy == "update":
                        update_set = ', '.join([f"{col}" = EXCLUDED.{col}" for col in columns])
                        sql = f"""
                        INSERT INTO {table_name} ({columns_str})
                        VALUES {values_str}
                        ON CONFLICT (id) DO UPDATE SET {update_set}
                        """
                    else:
                        sql = f"""
                        INSERT INTO {table_name} ({columns_str})
                        VALUES {values_str}
                        """

                    # 执行批量插入
                    result = await session.execute(text(sql), chunk)
                    await session.commit()

                    chunk_inserted = result.rowcount or len(chunk)
                    inserted_count += chunk_inserted
                    chunks_processed += 1

                    logger.debug("batch_insert_chunk_completed",
                               table_name=table_name,
                               chunk_size=len(chunk),
                               inserted=chunk_inserted,
                               chunk_num=chunks_processed)

            duration_ms = (time.time() - start_time) * 1000

            return {
                'total_count': total_count,
                'inserted_count': inserted_count,
                'duration_ms': duration_ms,
                'chunks': chunks_processed,
                'throughput_per_second': total_count / (duration_ms / 1000) if duration_ms > 0 else 0
            }

        except Exception as e:
            logger.error("batch_insert_error",
                        table_name=table_name,
                        total_count=total_count,
                        error=str(e))
            raise

    async def batch_update(self,
                         table_name: str,
                         update_data: Dict[str, Any],
                         where_clause: str,
                         params: Optional[Dict[str, Any]] = None) -> int:
        """批量更新数据"""
        start_time = time.time()

        try:
            db_pool = get_db_pool()
            async with db_pool.get_session() as session:
                # 构建更新SQL
                set_clause = ', '.join([f"{k}" = :{k}" for k in update_data.keys()])
                sql = f"UPDATE {table_name} SET {set_clause} WHERE {where_clause}"

                # 合并参数
                merged_params = {**update_data, **(params or {})}
                result = await session.execute(text(sql), merged_params)
                await session.commit()

                updated_count = result.rowcount or 0
                duration_ms = (time.time() - start_time) * 1000

                logger.info("batch_update_completed",
                           table_name=table_name,
                           updated_count=updated_count,
                           duration_ms=duration_ms)

                return updated_count

        except Exception as e:
            logger.error("batch_update_error",
                        table_name=table_name,
                        error=str(e))
            raise

    async def batch_delete(self,
                         table_name: str,
                         where_clause: str,
                         params: Optional[Dict[str, Any]] = None) -> int:
        """批量删除数据"""
        start_time = time.time()

        try:
            db_pool = get_db_pool()
            async with db_pool.get_session() as session:
                sql = f"DELETE FROM {table_name} WHERE {where_clause}"

                result = await session.execute(text(sql), params or {})
                await session.commit()

                deleted_count = result.rowcount or 0
                duration_ms = (time.time() - start_time) * 1000

                logger.info("batch_delete_completed",
                           table_name=table_name,
                           deleted_count=deleted_count,
                           duration_ms=duration_ms)

                return deleted_count

        except Exception as e:
            logger.error("batch_delete_error",
                        table_name=table_name,
                        error=str(e))
            raise


class CacheBatchProcessor:
    """缓存批量操作处理器"""

    def __init__(self, batch_size: int = 100):
        self.batch_size = batch_size

    async def batch_set(self, items: Dict[str, Any], ttl: int = 300) -> Dict[str, Any]:
        """批量设置缓存"""
        start_time = time.time()
        cache = get_multi_cache()

        success_count = 0
        error_count = 0

        # 分批处理
        items_list = list(items.items())
        for i in range(0, len(items_list), self.batch_size):
            batch = dict(items_list[i:i + self.batch_size])

            tasks = [
                cache.set(key, value, ttl=ttl)
                for key, value in batch.items()
            ]

            results = await asyncio.gather(*tasks, return_exceptions=True)

            for result in results:
                if isinstance(result, Exception):
                    error_count += 1
                else:
                    success_count += 1 if result else 0

        duration_ms = (time.time() - start_time) * 1000

        return {
            'total_items': len(items),
            'success_count': success_count,
            'error_count': error_count,
            'duration_ms': duration_ms
        }

    async def batch_get(self, keys: List[str]) -> Dict[str, Any]:
        """批量获取缓存"""
        start_time = time.time()
        cache = get_multi_cache()

        # 并发获取
        tasks = [cache.get(key) for key in keys]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        results_dict = {}
        success_count = 0
        error_count = 0

        for key, result in zip(keys, results):
            if isinstance(result, Exception):
                error_count += 1
            else:
                if result is not None:
                    results_dict[key] = result
                    success_count += 1

        duration_ms = (time.time() - start_time) * 1000

        return {
            'total_keys': len(keys),
            'found_count': len(results_dict),
            'success_count': success_count,
            'error_count': error_count,
            'results': results_dict,
            'duration_ms': duration_ms
        }

    async def batch_delete(self, keys: List[str]) -> Dict[str, Any]:
        """批量删除缓存"""
        start_time = time.time()
        cache = get_multi_cache()

        success_count = 0
        error_count = 0

        # 分批处理
        for i in range(0, len(keys), self.batch_size):
            batch = keys[i:i + self.batch_size]

            tasks = [cache.delete(key) for key in batch]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for result in results:
                if isinstance(result, Exception):
                    error_count += 1
                else:
                    success_count += 1 if result else 0

        duration_ms = (time.time() - start_time) * 1000

        return {
            'total_keys': len(keys),
            'success_count': success_count,
            'error_count': error_count,
            'duration_ms': duration_ms
        }


class BatchOperationManager:
    """批量操作管理器"""

    def __init__(self):
        self.jobs: Dict[str, BatchJob] = {}
        self.tasks: Dict[str, BatchTask] = {}
        self.running_jobs: Dict[str, asyncio.Task] = {}
        self.max_concurrent_jobs = 10
        self.job_history: List[BatchJob] = []
        self.max_history_size = 1000

        # 处理器
        self.db_processor = DatabaseBatchProcessor()
        self.cache_processor = CacheBatchProcessor()

    async def create_job(self,
                          name: str,
                          description: str,
                          tasks_data: List[Dict[str, Any]],
                          config: Optional[Dict[str, Any]] = None) -> str:
        """创建批量作业"""
        job_id = str(uuid.uuid())

        # 创建任务
        tasks = []
        for task_data in tasks_data:
            task = BatchTask(
                task_id=str(uuid.uuid()),
                operation_type=BatchOperationType(task_data.get('operation_type')),
                operation_data=task_data.get('operation_data'),
                max_retries=task_data.get('max_retries', 3),
                dependencies=task_data.get('dependencies', [])
            )
            tasks.append(task)
            self.tasks[task.task_id] = task

        # 创建作业
        job = BatchJob(
            job_id=job_id,
            name=name,
            description=description,
            tasks=tasks,
            config=config or {}
        )

        self.jobs[job_id] = job

        logger.info("batch_job_created",
                   job_id=job_id,
                   name=name,
                   total_tasks=len(tasks))

        return job_id

    async def submit_job(self, job_id: str) -> bool:
        """提交批量作业执行"""
        if job_id not in self.jobs:
            return False

        job = self.jobs[job_id]

        if job.status != BatchOperationStatus.PENDING:
            return False

        # 检查并发限制
        if len(self.running_jobs) >= self.max_concurrent_jobs:
            logger.warning("batch_job_queue_full", job_id=job_id)
            return False

        # 启动作业执行
        task = asyncio.create_task(self._execute_job(job))
        self.running_jobs[job_id] = task

        logger.info("batch_job_submitted", job_id=job_id, name=job.name)
        return True

    async def _execute_job(self, job: BatchJob):
        """执行批量作业"""
        job.status = BatchOperationStatus.RUNNING
        job.started_at = datetime.now()

        try:
            # 构建任务依赖图
            task_graph = self._build_task_graph(job.tasks)

            # 按依赖顺序执行任务
            completed_tasks = set()
            failed_tasks = set()

            while len(completed_tasks) + len(failed_tasks) < len(job.tasks):
                # 找到可以执行的任务（没有未完成的依赖）
                ready_tasks = [
                    task for task in job.tasks
                    if (task.task_id not in completed_tasks and
                        task.task_id not in failed_tasks and
                        all(dep in completed_tasks for dep in task.dependencies))
                ]

                if not ready_tasks:
                    # 检查是否有循环依赖
                    remaining_tasks = set(t.task_id for t in job.tasks)
                    remaining_tasks -= completed_tasks
                    remaining_tasks -= failed_tasks

                    if remaining_tasks:
                        logger.error("circular_dependency_detected",
                                   job_id=job.job_id,
                                   remaining_tasks=list(remaining_tasks))
                        break

                # 并发执行就绪的任务
                await self._execute_tasks_concurrently(ready_tasks, completed_tasks, failed_tasks)

                # 短暂休息避免过度占用CPU
                await asyncio.sleep(0.1)

            # 更新作业状态
            if len(failed_tasks) == 0:
                job.status = BatchOperationStatus.COMPLETED
            else:
                job.status = BatchOperationStatus.FAILED

            job.completed_at = datetime.now()

            # 添加到历史记录
            self._add_to_history(job)

            logger.info("batch_job_completed",
                       job_id=job.job_id,
                       name=job.name,
                       status=job.status.value,
                       total_tasks=len(job.tasks),
                       completed_tasks=len(completed_tasks),
                       failed_tasks=len(failed_tasks))

        except Exception as e:
            job.status = BatchOperationStatus.FAILED
            job.completed_at = datetime.now()
            job.error = str(e)

            logger.error("batch_job_execution_error",
                        job_id=job.job_id,
                        error=str(e))

        finally:
            # 清理运行中的作业记录
            self.running_jobs.pop(job.job_id, None)

    async def _execute_tasks_concurrently(self,
                                        tasks: List[BatchTask],
                                        completed_tasks: set,
                                        failed_tasks: set):
        """并发执行任务"""
        async def execute_single_task(task: BatchTask):
            await self._execute_task(task)

        # 并发执行任务
        await asyncio.gather(
            *[execute_single_task(task) for task in tasks],
            return_exceptions=True
        )

        # 更新任务状态
        for task in tasks:
            if task.status == BatchOperationStatus.COMPLETED:
                completed_tasks.add(task.task_id)
            elif task.status == BatchOperationStatus.FAILED:
                failed_tasks.add(task.task_id)

    async def _execute_task(self, task: BatchTask):
        """执行单个任务"""
        task.status = BatchOperationStatus.RUNNING
        task.started_at = datetime.now()

        try:
            if task.operation_type == BatchOperationType.DATABASE_INSERT:
                data = task.operation_data
                task.result = await self.db_processor.batch_insert(
                    table_name=data['table_name'],
                    data_list=data['data_list'],
                    conflict_strategy=data.get('conflict_strategy', 'ignore')
                )

            elif task.operation_type == BatchOperationType.DATABASE_UPDATE:
                data = task.operation_data
                task.result = await self.db_processor.batch_update(
                    table_name=data['table_name'],
                    update_data=data['update_data'],
                    where_clause=data['where_clause'],
                    params=data.get('params')
                )

            elif task.operation_type == BatchOperationType.DATABASE_DELETE:
                data = task.operation_data
                task.result = await self.db_processor.batch_delete(
                    table_name=data['table_name'],
                    where_clause=data['where_clause'],
                    params=data.get('params')
                )

            elif task.operation_type == BatchOperationType.CACHE_OPERATION:
                data = task.operation_data
                operation = data['operation']

                if operation == 'batch_set':
                    task.result = await self.cache_processor.batch_set(
                        items=data['items'],
                        ttl=data.get('ttl', 300)
                    )
                elif operation == 'batch_get':
                    task.result = await self.cache_processor.batch_get(data['keys'])
                elif operation == 'batch_delete':
                    task.result = await self.cache_processor.batch_delete(data['keys'])

            else:
                # 自定义任务处理
                handler = task.operation_data.get('handler')
                if handler and callable(handler):
                    task.result = await handler(task)

            task.status = BatchOperationStatus.COMPLETED
            task.completed_at = datetime.now()

        except Exception as e:
            task.error = str(e)
            task.retry_count += 1

            if task.retry_count <= task.max_retries:
                logger.warning("batch_task_retry",
                             task_id=task.task_id,
                             retry_count=task.retry_count,
                             max_retries=task.max_retries,
                             error=str(e))
                task.status = BatchOperationStatus.PENDING
            else:
                task.status = BatchOperationStatus.FAILED
                logger.error("batch_task_failed",
                            task_id=task.task_id,
                            retry_count=task.retry_count,
                            error=str(e))

    def _build_task_graph(self, tasks: List[BatchTask]) -> Dict[str, List[str]]:
        """构建任务依赖图"""
        graph = {}
        for task in tasks:
            graph[task.task_id] = task.dependencies
        return graph

    def _add_to_history(self, job: BatchJob):
        """添加作业到历史记录"""
        self.job_history.append(job)
        if len(self.job_history) > self.max_history_size:
            self.job_history = self.job_history[-self.max_history_size:]

    async def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """获取作业状态"""
        job = self.jobs.get(job_id)
        if job:
            return job.to_dict()
        return None

    async def list_jobs(self,
                         status_filter: Optional[BatchOperationStatus] = None,
                         limit: int = 50,
                         offset: int = 0) -> Dict[str, Any]:
        """列出作业"""
        jobs = list(self.jobs.values())

        # 状态过滤
        if status_filter:
            jobs = [j for j in jobs if j.status == status_filter]

        # 按创建时间倒序排序
        jobs.sort(key=lambda x: x.created_at, reverse=True)

        # 分页
        total_count = len(jobs)
        jobs = jobs[offset:offset + limit]

        return {
            'total_count': total_count,
            'jobs': [job.to_dict() for job in jobs],
            'limit': limit,
            'offset': offset
        }

    async def cancel_job(self, job_id: str) -> bool:
        """取消作业"""
        job = self.jobs.get(job_id)
        if not job:
            return False

        if job.status in [BatchOperationStatus.COMPLETED, BatchOperationStatus.FAILED]:
            return False

        # 取消运行中的任务
        if job_id in self.running_jobs:
            self.running_jobs[job_id].cancel()
            self.running_jobs.pop(job_id, None)

        job.status = BatchOperationStatus.CANCELLED
        job.completed_at = datetime.now()

        # 取消所有待执行的任务
        for task in job.tasks:
            if task.status == BatchOperationStatus.PENDING:
                task.status = BatchOperationStatus.CANCELLED
                task.completed_at = datetime.now()

        logger.info("batch_job_cancelled", job_id=job_id, name=job.name)
        return True

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        jobs = list(self.jobs.values())

        # 按状态分组
        status_counts = {}
        for status in BatchOperationStatus:
            status_counts[status.value] = len([j for j in jobs if j.status == status])

        # 计算性能指标
        completed_jobs = [j for j in jobs if j.status == BatchOperationStatus.COMPLETED]
        avg_duration = 0
        if completed_jobs:
            durations = [
                (j.completed_at - j.started_at).total_seconds()
                for j in completed_jobs
                if j.started_at and j.completed_at
            ]
            avg_duration = sum(durations) / len(durations) if durations else 0

        return {
            'total_jobs': len(jobs),
            'status_distribution': status_counts,
            'running_jobs': len(self.running_jobs),
            'completed_jobs': len(completed_jobs),
            'average_duration_seconds': avg_duration,
            'max_concurrent_jobs': self.max_concurrent_jobs
        }


# 全局批量操作管理器实例
_batch_manager: Optional[BatchOperationManager] = None


def get_batch_manager() -> BatchOperationManager:
    """获取批量操作管理器实例"""
    global _batch_manager
    if _batch_manager is None:
        _batch_manager = BatchOperationManager()
    return _batch_manager


# 便捷函数
async def batch_create_operation(operation_type: str,
                                data_list: List[Any],
                                **kwargs) -> Dict[str, Any]:
    """批量创建操作的便捷函数"""
    manager = get_batch_manager()

    tasks_data = [{
        'operation_type': operation_type,
        'operation_data': data
    } for data in data_list]

    job_id = await manager.create_job(
        name=f"Batch {operation_type}",
        description=f"批量创建 {len(data_list)} 个{operation_type}操作",
        tasks_data=tasks_data,
        config=kwargs
    )

    await manager.submit_job(job_id)
    return job_id


async def batch_update_records(table_name: str,
                                update_data: Dict[str, Any],
                                where_clause: str,
                                params: Optional[Dict[str, Any]] = None) -> int:
    """批量更新记录的便捷函数"""
    db_processor = DatabaseBatchProcessor()
    return await db_processor.batch_update(
        table_name=table_name,
        update_data=update_data,
        where_clause=where_clause,
        params=params
    )


async def batch_delete_records(table_name: str,
                                where_clause: str,
                                params: Optional[Dict[str, Any]] = None) -> int:
    """批量删除记录的便捷函数"""
    db_processor = DatabaseBatchProcessor()
    return await db_processor.batch_delete(
        table_name=table_name,
        where_clause=where_clause,
        params=params
    )