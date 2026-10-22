"""
V10 Database Models — Redfish Test Manager
=========================================
V10 架構終極正規化重點：
1. 移除所有為了向後相容而保留的 `project`、`old_plan_id` 等字串欄位。
2. `custom_subfolder` 字串改為 `subfolder_id` (UUID FK)，徹底解決資料夾更名造成的同步問題。
3. `category` 字串獨立為 `categories` 表格，支援未來使用者自訂類別。
4. 全面採用 UUID 作為 Foreign Key 關聯 (包含 `plan_id`, `project_id`, `category_id`, `subfolder_id`)。
"""

from sqlalchemy import DDL, Column, String, Boolean, Integer, ForeignKey, Text, UniqueConstraint, CheckConstraint, Index, text, event
from sqlalchemy.orm import declarative_base, relationship
import uuid

Base = declarative_base()


class Category(Base):
    __tablename__ = 'categories'
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=False, unique=True)
    
    testcases = relationship('TestCase', backref='category_obj', lazy='dynamic')


class Project(Base):
    __tablename__ = 'projects'
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=False, unique=True)

    plans = relationship(
        'ProjectPlan',
        backref='project_obj',
        cascade='all, delete-orphan',
        passive_deletes=True
    )


class ProjectInformation(Base):
    __tablename__ = 'project_information'
    project_id = Column(String(36), ForeignKey('projects.id', ondelete='CASCADE'), primary_key=True)
    document = Column(Text, nullable=False)
    revision = Column(Integer, nullable=False, default=1)
    updated_at = Column(String(64), nullable=False)


class ProjectPlan(Base):
    __tablename__ = 'project_plans'
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String(36), ForeignKey('projects.id', ondelete='CASCADE'), nullable=False)
    name = Column(String(255), nullable=False)
    category_order = Column(Text, nullable=True)
    folders_migrated = Column(Boolean, nullable=False, default=False)

    testcases = relationship(
        'TestCase',
        backref='plan_obj',
        cascade='all, delete-orphan',
        passive_deletes=True
    )
    tasks = relationship(
        'Task',
        backref='plan_obj',
        cascade='all, delete-orphan',
        passive_deletes=True
    )
    subfolders = relationship(
        'PlanSubfolder',
        backref='plan_obj',
        cascade='all, delete-orphan',
        passive_deletes=True
    )


class PlanSubfolder(Base):
    __tablename__ = 'plan_subfolders'
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    plan_id = Column(String(36), ForeignKey('project_plans.id', ondelete='CASCADE'), nullable=False)
    subfolder_name = Column(String(100), nullable=False)
    position = Column(Integer, default=0)
    
    testcases = relationship('TestCase', backref='subfolder_obj', passive_deletes=True)
    task_testcases = relationship('TaskTestCase', backref='subfolder_obj', passive_deletes=True)


class PlanFolder(Base):
    __tablename__ = 'plan_folders'
    __table_args__ = (
        Index('uq_folder_sibling', 'plan_id', text("coalesce(parent_id, '')"), 'normalized_name', unique=True),
    )
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    plan_id = Column(String(36), ForeignKey('project_plans.id', ondelete='CASCADE'), nullable=False)
    parent_id = Column(String(36), ForeignKey('plan_folders.id', ondelete='CASCADE'), nullable=True)
    name = Column(String(255), nullable=False)
    normalized_name = Column(String(255), nullable=False)
    position = Column(Integer, nullable=False, default=0)
    parent = relationship('PlanFolder', remote_side=[id])

    @property
    def path(self):
        names=[]; current=self
        while current:
            names.append(current.name);current=current.parent
        return '/'.join(reversed(names))

    def to_dict(self):
        return dict(id=self.id, plan_id=self.plan_id, parent_id=self.parent_id,
                    name=self.name, position=self.position, folder_path=self.path)


class TestCase(Base):
    __tablename__ = 'testcases'
    __table_args__ = (
        Index('uq_testcases_plan_name_version', 'plan_id', 'normalized_name', text("coalesce(source_version, '')"), unique=True),
    )
    system_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    family_id = Column(String(36), nullable=False, default=lambda: str(uuid.uuid4()))
    display_name = Column(String(255), nullable=False)
    normalized_name = Column(String(255), nullable=False)

    plan_id = Column(String(36), ForeignKey('project_plans.id', ondelete='CASCADE'), nullable=False)
    category_id = Column(String(36), ForeignKey('categories.id', ondelete='SET NULL'), nullable=True)
    subfolder_id = Column(String(36), ForeignKey('plan_subfolders.id', ondelete='SET NULL'), nullable=True)

    folder_id = Column(String(36), ForeignKey('plan_folders.id', ondelete='CASCADE'), nullable=True)
    folder_obj = relationship('PlanFolder')

    script_path = Column(String(255), nullable=False)
    script_kind = Column(String(20), nullable=False, default='steps')
    source_version = Column(String(50), nullable=True)
    repository_id = Column(String(36), nullable=True)
    settings_json = Column(Text, nullable=False, default='{}')
    settings_revision = Column(Integer, nullable=False, default=0)
    selected = Column(Boolean, default=True)
    position = Column(Integer, default=0)

    def to_dict(self):
        return {
            "id": self.system_id,
            "family_id": self.family_id,
            "folder_id": self.folder_id,
            "folder_path": self.folder_obj.path if self.folder_obj else "",
            "tc_name": self.display_name,
            "name_key": self.normalized_name,
            # 回傳關聯的字串供前端顯示
            "project": self.plan_obj.project_obj.name if self.plan_obj and self.plan_obj.project_obj else "",
            "plan_id": self.plan_id,
            "category": (self.folder_obj.parent or self.folder_obj).name if self.folder_obj else (self.category_obj.name if self.category_obj else ""),
            "script_path": self.script_path,
            "script_kind": self.script_kind,
            "source_version": self.source_version,
            "repository_id": self.repository_id,
            "settings_revision": self.settings_revision or 0,
            "custom_subfolder": self.folder_obj.name if self.folder_obj and self.folder_obj.parent_id else None,
            "selected": bool(self.selected)
            ,"position": self.position or 0
        }


@event.listens_for(TestCase, 'before_insert')
@event.listens_for(TestCase, 'before_update')
def _set_testcase_normalized_name(mapper, connection, target):
    target.normalized_name = (target.display_name or '').strip().casefold()


class Task(Base):
    __tablename__ = 'tasks'
    id = Column(String(100), primary_key=True)
    plan_id = Column(String(36), ForeignKey('project_plans.id', ondelete='CASCADE'), nullable=False)
    name = Column(String(255), nullable=False)
    environment_config = Column(Text, nullable=True)
    task_metadata = Column(Text, nullable=True)
    task_testcases = relationship(
        'TaskTestCase',
        backref='task_obj',
        cascade='all, delete-orphan',
        passive_deletes=True
    )
    execution_active = Column(Boolean, nullable=False, default=False)
    execution_selection = Column(Text, nullable=True)
    execution_token = Column(String(36), nullable=True)
    execution_worker_id = Column(String(100), nullable=True)
    execution_stop_requested = Column(Boolean, nullable=False, default=False)


class TaskTestCase(Base):
    __tablename__ = 'task_testcases'
    __table_args__ = (UniqueConstraint('task_id', 'testcase_id', name='uq_task_scope'),
                      CheckConstraint("status IN ('TBD','Running','Passed','Failed','Block')", name='ck_task_status'))
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    task_id = Column("task_id", String(100), ForeignKey('tasks.id', ondelete='CASCADE'), nullable=False)

    testcase_id = Column(String(36), ForeignKey('testcases.system_id', ondelete='CASCADE'), nullable=False)
    
    position = Column(Integer, default=0)
    selected = Column(Boolean, default=True)
    subfolder_id = Column(String(36), ForeignKey('plan_subfolders.id', ondelete='SET NULL'), nullable=True)
    status = Column(String(50), nullable=False, default='TBD')
    manual_override_json = Column(Text, nullable=True)
    result_json = Column(Text, nullable=True)
    log_text = Column(Text, nullable=True)
    api_log_text = Column(Text, nullable=True)
    bug_id = Column(String(100), nullable=True)
    executed_at = Column(String(50), nullable=True)
    needs_retest = Column(Boolean, nullable=False, default=False)


class RepositoryCase(Base):
    __tablename__ = 'repository_cases'
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    source_version = Column(String(50), nullable=False, unique=True)
    source_text = Column(Text, nullable=False)


class RepositoryFolder(Base):
    __tablename__ = 'repository_folders'
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    normalized_name = Column(String(255), nullable=False, unique=True)


class RepositoryFolderCase(Base):
    __tablename__ = 'repository_folder_cases'
    repository_id = Column(String(36), ForeignKey('repository_cases.id', ondelete='CASCADE'), primary_key=True)
    folder_id = Column(String(36), ForeignKey('repository_folders.id', ondelete='CASCADE'), nullable=False)


class RepositoryFolderNode(Base):
    __tablename__ = 'repository_folder_nodes'
    folder_id = Column(String(36), ForeignKey('repository_folders.id', ondelete='CASCADE'), primary_key=True)
    parent_id = Column(String(36), ForeignKey('repository_folders.id', ondelete='RESTRICT'), nullable=True)
    position = Column(Integer, nullable=False, default=0)


class CaseListOrder(Base):
    """Explicit user order; absence means natural Test Case number order."""
    __tablename__ = 'case_list_orders'
    scope = Column(String(100), primary_key=True)
    folder = Column(String(36), primary_key=True, default='')
    case_ids = Column(Text, nullable=False, default='[]')


class PlanningTask(Base):
    """Non-executable Plan work, owned by a Project and optional saved SKU."""
    __tablename__ = 'planning_tasks'
    id = Column(String(100), primary_key=True)
    project_id = Column(String(36), ForeignKey('projects.id', ondelete='CASCADE'), nullable=False)
    sku_id = Column(String(100), nullable=True)
    sku_name = Column(String(255), nullable=False, default='')
    name = Column(String(255), nullable=False)
    task_metadata = Column(Text, nullable=True)


class PlanSKU(Base):
    __tablename__ = 'plan_skus'
    plan_id = Column(String(36), ForeignKey('project_plans.id', ondelete='CASCADE'), primary_key=True)
    sku_id = Column(String(100), nullable=False)


class TaskNameSeries(Base):
    __tablename__ = 'task_name_series'
    scope = Column(String(500), primary_key=True)
    last_number = Column(Integer, nullable=False)


class TaskNameReservation(Base):
    """Issued names survive Task deletion, so numbers are never recycled."""
    __tablename__ = 'task_name_reservations'
    __table_args__ = (UniqueConstraint('project_id', 'task_type', 'name', name='uq_issued_task_name'),)
    task_id = Column(String(100), primary_key=True)
    project_id = Column(String(36), ForeignKey('projects.id', ondelete='CASCADE'), nullable=False)
    task_type = Column(String(10), nullable=False)
    sku_id = Column(String(100), nullable=True)
    sku_name = Column(String(255), nullable=False, default='')
    plan_id = Column(String(36), nullable=True)
    name = Column(String(255), nullable=False)


class GlobalTaskName(Base):
    """Global, permanent Task-name claims, independent of Project/Task deletion."""
    __tablename__ = 'global_task_names'
    name_key = Column(String(255), primary_key=True)
    name = Column(String(255), nullable=False)
    task_id = Column(String(100), nullable=False)


class ScheduleDayOverride(Base):
    __tablename__ = 'schedule_day_overrides'
    date = Column(String(10), primary_key=True)
    is_working = Column(Boolean, nullable=False)


class TaskScheduleHistory(Base):
    """Append-only planning changes; retained even when the owning Task is removed."""
    __tablename__ = 'task_schedule_history'
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    # Either Task type may own this ID. No cascading FK: history must never be deleted.
    task_id = Column(String(100), nullable=False, index=True)
    task_type = Column(String(10), nullable=False)
    task_name = Column(String(255), nullable=False)
    created_at = Column(String(64), nullable=False)
    previous_start_date = Column(String(10), nullable=False)
    previous_end_date = Column(String(10), nullable=False)
    start_date = Column(String(10), nullable=False)
    end_date = Column(String(10), nullable=False)
    history = Column(Text, nullable=False)


for operation in ('UPDATE', 'DELETE'):
    event.listen(TaskScheduleHistory.__table__, 'after_create', DDL(
        "CREATE TRIGGER task_schedule_history_no_" + operation.lower() +
        " BEFORE " + operation + " ON task_schedule_history "
        "BEGIN SELECT RAISE(ABORT, 'Task History is immutable'); END"
    ).execute_if(dialect='sqlite'))
