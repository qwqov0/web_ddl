"""
Python 程序设计大作业 - 班级作业管理系统 (Web版)
功能：作业发布、倒计时可视化、双标签分类、归档、JSON持久化存储、模拟时间调试
"""

import streamlit as st
import os
from datetime import datetime, timedelta
import time
import json

# === 全局常量定义 ===
DATA_FILE = "assignment_data.json"  # 核心作业数据
CONFIG_FILE = "assignment_config.json"  # 标签配置文件
HISTORY_FILE = "assignment_archive.json"  # 历史归档文件

# ==========================================
# 0. UI 美化 (CSS)
# ==========================================
def inject_custom_css():
    st.markdown("""
        <style>
        /* 微信绿风格按钮 */
        div.stButton > button:first-child[kind="primary"] {
            background-color: #07c160;
            border-color: #07c160;
            color: white;
        }
        div.stButton > button:first-child[kind="primary"]:hover {
            background-color: #05a050;
            border-color: #05a050;
        }
        /* 绿色进度条 */
        .stProgress > div > div > div > div {
            background-color: #07c160;
        }
        </style>
    """, unsafe_allow_html=True)

# ==========================================
# 1. 配置管理模块 (JSON I/O)
# ==========================================
def load_tags():
    default_config = {
        "subjects": ["高等数学", "Python程序设计", "大学英语", "思修", "专业课"],
        "categories": ["课后习题", "实验报告", "期末论文", "小组展示", "随堂测验"]
    }
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except: return default_config
    return default_config

def save_tags(config):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

# ==========================================
# 2. 核心数据结构 (Linked List + JSON)
# ==========================================
class HomeworkNode:
    def __init__(self, name, deadline_str, start_date_str=None, subject="其他", category="作业", priority="普通"):
        self.name = name
        self.deadline = deadline_str
        self.subject = subject
        self.category = category
        self.priority = priority
        if start_date_str:
            try: self.start_date = datetime.strptime(start_date_str, "%Y-%m-%d %H:%M")
            except: self.start_date = datetime.now()
        else: self.start_date = datetime.now()
        self.next = None

    def to_dict(self):
        return {
            "name": self.name,
            "deadline": self.deadline,
            "start_date": self.start_date.strftime("%Y-%m-%d %H:%M"),
            "subject": self.subject,
            "category": self.category,
            "priority": self.priority
        }

class HomeworkList:
    def __init__(self):
        self.head = None
        self.load_from_file()

    def save_to_file(self):
        self.sort_by_deadline()
        data_list = []
        curr = self.head
        while curr:
            data_list.append(curr.to_dict())
            curr = curr.next
        try:
            with open(DATA_FILE, "w", encoding="utf-8") as f:
                json.dump(data_list, f, ensure_ascii=False, indent=2)
        except Exception as e:
            st.error(f"保存失败: {e}")

    def load_from_file(self):
        if not os.path.exists(DATA_FILE): return
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data_list = json.load(f)
                self.head = None
                for item in data_list:
                    self.add_node_internal(
                        item.get("name"), item.get("deadline"), item.get("start_date"),
                        item.get("subject", "未分类"), item.get("category", "作业"), item.get("priority", "普通")
                    )
        except: pass

    def add_node_internal(self, name, deadline_str, start_date_str, subject, category, priority):
        new_node = HomeworkNode(name, deadline_str, start_date_str, subject, category, priority)
        if not self.head: self.head = new_node
        else:
            curr = self.head
            while curr.next: curr = curr.next
            curr.next = new_node

    def add_or_update(self, name, deadline_str, subject, category, priority):
        curr = self.head
        while curr:
            if curr.name == name:
                curr.deadline = deadline_str
                curr.subject = subject
                curr.category = category
                curr.priority = priority
                self.save_to_file()
                return "updated"
            curr = curr.next
        self.add_node_internal(name, deadline_str, None, subject, category, priority)
        self.save_to_file()
        return "added"

    def archive_task(self, target_name):
        curr = self.head
        prev = None
        while curr:
            if curr.name == target_name:
                # 写入历史JSON
                history_data = []
                if os.path.exists(HISTORY_FILE):
                    try:
                        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                            history_data = json.load(f)
                    except: pass

                history_item = curr.to_dict()
                history_item["finished_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")
                history_data.append(history_item)

                with open(HISTORY_FILE, "w", encoding="utf-8") as f:
                    json.dump(history_data, f, ensure_ascii=False, indent=2)

                # 链表删除
                if prev: prev.next = curr.next
                else: self.head = curr.next
                self.save_to_file()
                return True
            prev = curr
            curr = curr.next
        return False

    def sort_by_deadline(self):
        if not self.head or not self.head.next: return
        swapped = True
        while swapped:
            swapped = False
            curr = self.head
            while curr.next:
                if curr.deadline > curr.next.deadline:
                    # 交换所有数据
                    curr.name, curr.next.name = curr.next.name, curr.name
                    curr.deadline, curr.next.deadline = curr.next.deadline, curr.deadline
                    curr.start_date, curr.next.start_date = curr.next.start_date, curr.start_date
                    curr.subject, curr.next.subject = curr.next.subject, curr.subject
                    curr.category, curr.next.category = curr.next.category, curr.category
                    curr.priority, curr.next.priority = curr.next.priority, curr.priority
                    swapped = True
                curr = curr.next

    def get_all_data(self):
        self.sort_by_deadline()
        data = []
        curr = self.head
        while curr:
            data.append(curr)
            curr = curr.next
        return data

# ==========================================
# 3. Streamlit 页面渲染
# ==========================================
st.set_page_config(page_title="班级作业管理系统", page_icon="🎓", layout="centered")
inject_custom_css()

if 'hw_list' not in st.session_state: st.session_state.hw_list = HomeworkList()
if 'time_offset' not in st.session_state: st.session_state.time_offset = timedelta(0)
if 'tags_config' not in st.session_state: st.session_state.tags_config = load_tags()

# --- 侧边栏 ---
with st.sidebar:
    st.header("⚙️ 系统设置")

    # 标签管理
    with st.expander("🏷️ 标签管理", expanded=False):
        tab1, tab2 = st.tabs(["➕ 添加", "➖ 删除"])
        with tab1:
            n_s = st.text_input("新增科目")
            if st.button("加科目") and n_s:
                if n_s not in st.session_state.tags_config["subjects"]:
                    st.session_state.tags_config["subjects"].append(n_s)
                    save_tags(st.session_state.tags_config)
                    st.rerun()
            n_c = st.text_input("新增类型")
            if st.button("加类型") and n_c:
                if n_c not in st.session_state.tags_config["categories"]:
                    st.session_state.tags_config["categories"].append(n_c)
                    save_tags(st.session_state.tags_config)
                    st.rerun()
        with tab2:
            d_s = st.selectbox("删科目", ["(无)"] + st.session_state.tags_config["subjects"])
            if st.button("删科目") and d_s != "(无)":
                st.session_state.tags_config["subjects"].remove(d_s)
                save_tags(st.session_state.tags_config)
                st.rerun()
            d_c = st.selectbox("删类型", ["(无)"] + st.session_state.tags_config["categories"])
            if st.button("删类型") and d_c != "(无)":
                st.session_state.tags_config["categories"].remove(d_c)
                save_tags(st.session_state.tags_config)
                st.rerun()

    # 🐛 时间调试控制台 (已修复: 增加 +1小时)
    with st.expander("🐛 演示控制台 (模拟时间)", expanded=True):
        @st.fragment(run_every=1)
        def show_clock():
            now = datetime.now() + st.session_state.time_offset
            st.info(f"模拟时间: {now.strftime('%H:%M:%S')}")
        show_clock()

        # 使用 3 列布局，方便操作
        c1, c2, c3 = st.columns([1, 1, 1])
        if c1.button("⏩ +1时"):
            st.session_state.time_offset += timedelta(hours=1)
            st.rerun()
        if c2.button("🚀 +1天"):
            st.session_state.time_offset += timedelta(days=1)
            st.rerun()
        if c3.button("🔄 重置"):
            st.session_state.time_offset = timedelta(0)
            st.rerun()

# --- 主界面 ---
st.title("🎓 班级作业管理系统")
st.caption("Release Version 1.1 | JSON存档 | 实时演示")

# --- 发布区 ---
with st.container(border=True):
    st.subheader("📢 发布作业")
    name = st.text_input("作业内容", placeholder="例如：完成 Python 实验报告")
    c1, c2 = st.columns(2)
    subj = c1.selectbox("所属科目", st.session_state.tags_config["subjects"])
    cat = c2.selectbox("作业类型", st.session_state.tags_config["categories"])

    c3, c4, c5 = st.columns([2, 2, 1.5])
    d = c3.date_input("截止日期", min_value=datetime.now())
    t = c4.time_input("截止时间", value=datetime.strptime("23:59", "%H:%M").time())
    p = c5.select_slider("优先级", ["🟢 普通", "🟠 重要", "🔴 紧急"])

    if st.button("🚀 立即发布", use_container_width=True, type="primary"):
        if name:
            dt = datetime.combine(d, t).strftime("%Y-%m-%d %H:%M")
            p_val = p.split(" ")[1]
            st.session_state.hw_list.add_or_update(name, dt, subj, cat, p_val)
            st.toast("发布成功，数据已保存！")
            time.sleep(0.5)
            st.rerun()

st.divider()

# --- 列表显示区 ---
@st.fragment(run_every=1)
def show_list():
    now = datetime.now() + st.session_state.time_offset
    tasks = st.session_state.hw_list.get_all_data()

    if not tasks:
        st.success("🎉 太棒了！当前没有待办作业！")
        return

    st.subheader("📋 任务列表")
    for i, task in enumerate(tasks):
        try:
            end = datetime.strptime(task.deadline, "%Y-%m-%d %H:%M")
            total = (end - task.start_date).total_seconds()
            left = (end - now).total_seconds()
            pct = max(0.0, min(1.0, (total - left) / total)) if total > 0 else 1.0
        except: pct, left = 0, 0

        # 文案逻辑
        if left <= 0: status = "🔴 已截止"
        else:
            d, h, m, s = int(left//86400), int((left%86400)//3600), int((left%3600)//60), int(left%60)
            if d > 0: status = f"🔵 剩 {d}天 {h}时"
            elif h > 0: status = f"🟠 剩 {h}时 {m}分"
            else: status = f"⚡ 仅剩 {m}分 {s}秒" # 小于1小时显示秒

        # 样式
        subj_colors = {"高等数学": "blue", "Python程序设计": "green", "大学英语": "orange", "思修": "red"}
        s_color = subj_colors.get(task.subject, "gray")
        p_icon = "🔥" if task.priority == "紧急" else ("⭐" if task.priority == "重要" else "")

        # 渲染卡片
        with st.container(border=True):
            c_info, c_bar, c_act = st.columns([3, 2, 1.2])
            with c_info:
                st.markdown(f"#### {p_icon} {task.name}")
                st.markdown(f"""
                    <span style='color:{s_color}; border:1px solid {s_color}; padding:2px 4px; border-radius:3px; font-size:0.8em'>{task.subject}</span>
                    <span style='color:gray; background:#f0f0f0; padding:2px 4px; border-radius:3px; font-size:0.8em; margin-left:5px'>📂 {task.category}</span>
                    <span style='color:gray; font-size:0.8em; margin-left:10px'>🏁 {task.deadline}</span>
                """, unsafe_allow_html=True)
            with c_bar:
                st.write(f"**{status}**")
                st.progress(pct)
            with c_act:
                with st.popover("⚙️ 操作", use_container_width=True):
                    new_n = st.text_input("修正名称", value=task.name, key=f"n_{i}")
                    s_list = st.session_state.tags_config["subjects"]
                    c_list = st.session_state.tags_config["categories"]
                    # 容错索引
                    curr_s_idx = s_list.index(task.subject) if task.subject in s_list else 0
                    curr_c_idx = c_list.index(task.category) if task.category in c_list else 0
                    new_s = st.selectbox("修正科目", s_list, index=curr_s_idx, key=f"s_{i}")
                    new_c = st.selectbox("修正类型", c_list, index=curr_c_idx, key=f"c_{i}")

                    if st.button("💾 保存", key=f"sv_{i}"):
                        st.session_state.hw_list.add_or_update(new_n, task.deadline, new_s, new_c, task.priority)
                        st.rerun()
                    if st.button("✅ 完成并归档", key=f"fin_{i}", type="primary"):
                        st.session_state.hw_list.archive_task(task.name)
                        st.balloons()
                        st.toast("作业已归档！")
                        time.sleep(1)
                        st.rerun()

show_list()

# --- 历史归档区 ---
with st.expander("📜 历史归档 (已完成)"):
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                history_data = json.load(f)
                if history_data:
                    display_data = []
                    # 倒序显示，最新的在最上面
                    for h in reversed(history_data):
                        display_data.append({
                            "作业名称": h.get("name"),
                            "科目": h.get("subject"),
                            "完成时间": h.get("finished_at")
                        })
                    st.dataframe(display_data, use_container_width=True)
                else: st.write("暂无历史数据")
        except: st.write("读取错误")
    else: st.write("暂无历史数据")