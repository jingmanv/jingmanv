"""
桌面版 TODO 待办事项图形界面工具
================================

技术栈：
    - Python 3
    - CustomTkinter（现代扁平化界面）
    - tkinter.messagebox（删除二次确认）

特性：
    - 左右分栏布局：左侧导航菜单 + 右侧主操作区
    - 五个视图：今天 / 明天 / 本周 / 收件箱 / 已完成
    - 顶部快速添加栏：任务标题输入框 + 截止日期输入框 + 添加按钮
    - 任务行：复选框、标题、日期标签、删除按钮
    - 本地 JSON 持久化（同级目录下 todos.json）
    - 支持暗色/亮色主题切换

安装依赖：
    pip install customtkinter

运行：
    python todo_app.py
"""

from __future__ import annotations

import json
import os
import re
import uuid
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta
from tkinter import messagebox
from typing import Callable, Dict, List, Optional

import customtkinter as ctk


# ---------------------------------------------------------------------------
# 数据层
# ---------------------------------------------------------------------------

DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "todos.json")
DATE_FMT = "%Y-%m-%d"
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


@dataclass
class Todo:
    """单条待办任务的数据结构。"""

    title: str
    date: Optional[str] = None  # "YYYY-MM-DD" 或 None
    completed: bool = False
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Todo":
        return cls(
            id=data.get("id") or uuid.uuid4().hex,
            title=str(data.get("title", "")).strip(),
            date=data.get("date") or None,
            completed=bool(data.get("completed", False)),
            created_at=data.get("created_at") or datetime.now().isoformat(timespec="seconds"),
        )


class TodoStore:
    """负责 todos.json 的加载与保存，并对内存中的任务列表进行增删改查。"""

    def __init__(self, path: str = DATA_FILE) -> None:
        self.path = path
        self.todos: List[Todo] = []
        self.load()

    # ---------- 持久化 ----------
    def load(self) -> None:
        """读取 JSON 文件；不存在或损坏时回退为空列表，并备份损坏文件。"""
        if not os.path.exists(self.path):
            self.todos = []
            return
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            if not isinstance(raw, list):
                raise ValueError("todos.json 顶层必须是数组")
            self.todos = [Todo.from_dict(item) for item in raw if isinstance(item, dict)]
        except (json.JSONDecodeError, ValueError, OSError) as exc:
            # 备份损坏文件，避免覆盖丢失
            try:
                backup = self.path + ".broken"
                os.replace(self.path, backup)
                print(f"[警告] todos.json 损坏 ({exc})，已备份到 {backup}")
            except OSError:
                pass
            self.todos = []

    def save(self) -> None:
        """原子写入：先写临时文件再替换。"""
        tmp = self.path + ".tmp"
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump([t.to_dict() for t in self.todos], f, ensure_ascii=False, indent=2)
            os.replace(tmp, self.path)
        except OSError as exc:
            print(f"[错误] 保存 todos.json 失败：{exc}")

    # ---------- CRUD ----------
    def add(self, title: str, due: Optional[str]) -> Todo:
        todo = Todo(title=title.strip(), date=due or None)
        self.todos.append(todo)
        self.save()
        return todo

    def delete(self, todo_id: str) -> None:
        self.todos = [t for t in self.todos if t.id != todo_id]
        self.save()

    def set_completed(self, todo_id: str, completed: bool) -> None:
        for t in self.todos:
            if t.id == todo_id:
                t.completed = completed
                break
        self.save()

    # ---------- 过滤 ----------
    def filter_by_view(self, view: str) -> List[Todo]:
        """根据视图名称返回筛选后的任务列表。"""
        today = date.today()
        tomorrow = today + timedelta(days=1)
        # 自然周：周一至周日
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)

        def parse(d: Optional[str]) -> Optional[date]:
            if not d:
                return None
            try:
                return datetime.strptime(d, DATE_FMT).date()
            except ValueError:
                return None

        results: List[Todo] = []
        for t in self.todos:
            d = parse(t.date)
            if view == "inbox":
                if not t.completed:
                    results.append(t)
            elif view == "today":
                if not t.completed and d == today:
                    results.append(t)
            elif view == "tomorrow":
                if not t.completed and d == tomorrow:
                    results.append(t)
            elif view == "week":
                if not t.completed and d is not None and week_start <= d <= week_end:
                    results.append(t)
            elif view == "completed":
                if t.completed:
                    results.append(t)

        # 排序：按日期升序（无日期排最后），再按创建时间
        results.sort(key=lambda x: (x.date or "9999-99-99", x.created_at))
        return results


# ---------------------------------------------------------------------------
# 界面层
# ---------------------------------------------------------------------------

# 视图定义：key -> (中文标题, 顺序)
VIEWS = [
    ("today", "今天"),
    ("tomorrow", "明天"),
    ("week", "本周"),
    ("inbox", "收件箱"),
    ("completed", "已完成"),
]


class TaskRow(ctk.CTkFrame):
    """单条任务的可视化行：复选框 + 标题 + 日期 + 删除按钮。"""

    def __init__(
        self,
        master,
        todo: Todo,
        on_toggle: Callable[[str, bool], None],
        on_delete: Callable[[str], None],
    ) -> None:
        super().__init__(master, corner_radius=8, fg_color=("gray92", "gray20"))
        self.todo = todo
        self.on_toggle = on_toggle
        self.on_delete = on_delete

        self.grid_columnconfigure(1, weight=1)

        # 完成状态复选框
        self.var = ctk.BooleanVar(value=todo.completed)
        self.checkbox = ctk.CTkCheckBox(
            self,
            text="",
            variable=self.var,
            width=24,
            command=self._toggle,
        )
        self.checkbox.grid(row=0, column=0, padx=(12, 8), pady=10)

        # 标题（完成时显示为灰色，未删除线效果用颜色弱化代替）
        title_color = ("gray50", "gray55") if todo.completed else ("gray10", "gray90")
        self.title_label = ctk.CTkLabel(
            self,
            text=todo.title,
            anchor="w",
            text_color=title_color,
            font=ctk.CTkFont(size=14),
        )
        self.title_label.grid(row=0, column=1, sticky="ew", padx=4, pady=10)

        # 日期标签
        if todo.date:
            self.date_label = ctk.CTkLabel(
                self,
                text=self._format_date(todo.date),
                text_color=self._date_color(todo.date, todo.completed),
                font=ctk.CTkFont(size=12),
            )
            self.date_label.grid(row=0, column=2, padx=8, pady=10)

        # 删除按钮
        self.delete_btn = ctk.CTkButton(
            self,
            text="✕",
            width=28,
            height=28,
            fg_color="transparent",
            hover_color=("gray80", "gray30"),
            text_color=("gray40", "gray60"),
            command=self._delete,
        )
        self.delete_btn.grid(row=0, column=3, padx=(4, 8), pady=10)

    # ----- 内部回调 -----
    def _toggle(self) -> None:
        self.on_toggle(self.todo.id, bool(self.var.get()))

    def _delete(self) -> None:
        if messagebox.askyesno("删除确认", f"确定要删除任务“{self.todo.title}”吗？"):
            self.on_delete(self.todo.id)

    @staticmethod
    def _format_date(d: str) -> str:
        try:
            dt = datetime.strptime(d, DATE_FMT).date()
        except ValueError:
            return d
        today = date.today()
        delta = (dt - today).days
        if delta == 0:
            return "今天"
        if delta == 1:
            return "明天"
        if delta == -1:
            return "昨天"
        return d

    @staticmethod
    def _date_color(d: str, completed: bool):
        if completed:
            return ("gray55", "gray55")
        try:
            dt = datetime.strptime(d, DATE_FMT).date()
        except ValueError:
            return ("gray40", "gray60")
        today = date.today()
        if dt < today:
            return ("#d9534f", "#ff6b6b")  # 已过期：红
        if dt == today:
            return ("#1f7a3a", "#4fd17a")  # 今天：绿
        return ("gray40", "gray70")


class TodoApp(ctk.CTk):
    """主窗口：左侧导航 + 右侧主区。"""

    def __init__(self) -> None:
        super().__init__()
        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")

        self.title("TODO · 待办事项")
        self.geometry("980x640")
        self.minsize(820, 520)

        self.store = TodoStore()
        self.current_view: str = "today"
        self.nav_buttons: Dict[str, ctk.CTkButton] = {}

        self._build_layout()
        self._select_view(self.current_view)

    # --------------------------- UI 构建 ---------------------------
    def _build_layout(self) -> None:
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._build_sidebar()
        self._build_main_area()

    def _build_sidebar(self) -> None:
        sidebar = ctk.CTkFrame(self, width=200, corner_radius=0)
        sidebar.grid(row=0, column=0, sticky="nsw")
        sidebar.grid_rowconfigure(len(VIEWS) + 2, weight=1)

        title = ctk.CTkLabel(
            sidebar,
            text="📝  我的待办",
            font=ctk.CTkFont(size=18, weight="bold"),
            anchor="w",
        )
        title.grid(row=0, column=0, padx=20, pady=(24, 16), sticky="ew")

        for idx, (key, label) in enumerate(VIEWS, start=1):
            btn = ctk.CTkButton(
                sidebar,
                text=f"  {label}",
                anchor="w",
                height=38,
                corner_radius=8,
                fg_color="transparent",
                hover_color=("gray85", "gray25"),
                text_color=("gray10", "gray90"),
                font=ctk.CTkFont(size=14),
                command=lambda k=key: self._select_view(k),
            )
            btn.grid(row=idx, column=0, padx=10, pady=2, sticky="ew")
            self.nav_buttons[key] = btn

        # 底部：主题切换
        appearance = ctk.CTkOptionMenu(
            sidebar,
            values=["System", "Light", "Dark"],
            command=lambda mode: ctk.set_appearance_mode(mode),
            width=160,
        )
        appearance.set("System")
        appearance.grid(row=len(VIEWS) + 3, column=0, padx=20, pady=20, sticky="s")

    def _build_main_area(self) -> None:
        main = ctk.CTkFrame(self, corner_radius=0, fg_color=("gray96", "gray14"))
        main.grid(row=0, column=1, sticky="nsew")
        main.grid_columnconfigure(0, weight=1)
        main.grid_rowconfigure(2, weight=1)

        # 标题
        self.header_label = ctk.CTkLabel(
            main,
            text="今天",
            font=ctk.CTkFont(size=24, weight="bold"),
            anchor="w",
        )
        self.header_label.grid(row=0, column=0, sticky="ew", padx=28, pady=(24, 8))

        # 快速添加栏
        add_bar = ctk.CTkFrame(main, corner_radius=10)
        add_bar.grid(row=1, column=0, sticky="ew", padx=24, pady=(0, 12))
        add_bar.grid_columnconfigure(0, weight=1)

        self.title_entry = ctk.CTkEntry(
            add_bar,
            placeholder_text="添加任务，回车快速保存…",
            height=40,
            font=ctk.CTkFont(size=14),
        )
        self.title_entry.grid(row=0, column=0, sticky="ew", padx=(12, 8), pady=10)
        self.title_entry.bind("<Return>", lambda _e: self._add_task())

        self.date_entry = ctk.CTkEntry(
            add_bar,
            placeholder_text="YYYY-MM-DD（可空）",
            width=170,
            height=40,
            font=ctk.CTkFont(size=13),
        )
        self.date_entry.grid(row=0, column=1, padx=4, pady=10)
        self.date_entry.bind("<Return>", lambda _e: self._add_task())

        add_btn = ctk.CTkButton(
            add_bar,
            text="添加",
            width=90,
            height=40,
            command=self._add_task,
        )
        add_btn.grid(row=0, column=2, padx=(4, 12), pady=10)

        # 任务列表（可滚动）
        self.list_frame = ctk.CTkScrollableFrame(
            main,
            corner_radius=10,
            fg_color=("white", "gray17"),
        )
        self.list_frame.grid(row=2, column=0, sticky="nsew", padx=24, pady=(0, 24))
        self.list_frame.grid_columnconfigure(0, weight=1)

        # 空状态标签（按需显示）
        self.empty_label = ctk.CTkLabel(
            self.list_frame,
            text="",
            font=ctk.CTkFont(size=13),
            text_color=("gray55", "gray55"),
        )

    # --------------------------- 行为逻辑 ---------------------------
    def _select_view(self, key: str) -> None:
        """切换视图并刷新列表。"""
        self.current_view = key
        # 高亮当前导航
        for k, btn in self.nav_buttons.items():
            if k == key:
                btn.configure(fg_color=("gray80", "gray28"), text_color=("#1f6feb", "#5aa9ff"))
            else:
                btn.configure(fg_color="transparent", text_color=("gray10", "gray90"))
        # 更新标题
        label = dict(VIEWS)[key]
        self.header_label.configure(text=label)
        self._refresh_list()

    def _refresh_list(self) -> None:
        """根据当前视图刷新右侧任务列表。"""
        for child in self.list_frame.winfo_children():
            child.destroy()

        todos = self.store.filter_by_view(self.current_view)
        if not todos:
            empty = ctk.CTkLabel(
                self.list_frame,
                text=self._empty_text(),
                font=ctk.CTkFont(size=14),
                text_color=("gray55", "gray55"),
            )
            empty.grid(row=0, column=0, pady=40)
            return

        for i, t in enumerate(todos):
            row = TaskRow(
                self.list_frame,
                todo=t,
                on_toggle=self._on_toggle,
                on_delete=self._on_delete,
            )
            row.grid(row=i, column=0, sticky="ew", padx=6, pady=4)

    def _empty_text(self) -> str:
        return {
            "today": "今天还没有任务，先休息一下 ☕",
            "tomorrow": "明天暂无安排 🌤",
            "week": "本周清单为空 ✨",
            "inbox": "收件箱空空如也，添加一个任务开始吧 ✍️",
            "completed": "还没有完成的任务，加油！💪",
        }.get(self.current_view, "暂无任务")

    def _add_task(self) -> None:
        title = self.title_entry.get().strip()
        if not title:
            return
        due_raw = self.date_entry.get().strip()
        due: Optional[str] = None
        if due_raw:
            if not DATE_RE.match(due_raw):
                messagebox.showwarning("日期格式错误", "日期请使用 YYYY-MM-DD 格式，或留空。")
                return
            try:
                datetime.strptime(due_raw, DATE_FMT)
            except ValueError:
                messagebox.showwarning("日期无效", "请输入合法日期，如 2026-01-15。")
                return
            due = due_raw

        self.store.add(title, due)
        self.title_entry.delete(0, "end")
        self.date_entry.delete(0, "end")
        self._refresh_list()

    def _on_toggle(self, todo_id: str, completed: bool) -> None:
        self.store.set_completed(todo_id, completed)
        # 切换完成状态后通常会从当前视图消失（除"已完成"视图），刷新即可
        self._refresh_list()

    def _on_delete(self, todo_id: str) -> None:
        self.store.delete(todo_id)
        self._refresh_list()


# ---------------------------------------------------------------------------
# 入口
# ---------------------------------------------------------------------------

def main() -> None:
    app = TodoApp()
    app.mainloop()


if __name__ == "__main__":
    main()
