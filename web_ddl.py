import streamlit as st
import os
from datetime import datetime
import time
import json
import requests

# ==========================================
# 0. 云端统一存储模块
# ==========================================
LOCAL_BACKUP = "cloud_backup.json"

def get_default_state():
    return {
        "config": {
            # 这里我帮你把默认标签泛化了一下，你可以自己在网页里继续修改
            "subjects": ["学习", "生活", "工作", "社团", "其他"],
            "categories": ["日常杂务", "重要报告", "课后作业", "会议", "出行"]
        },
        "data": [],
        "history": []
    }

def fetch_from_cloud():
    if "BIN_ID" in st.secrets and "API_KEY" in st.secrets:
        try:
            url = f"https://api.jsonbin.io/v3/b/{st.secrets['BIN_ID']}/latest"
            headers = {"X-Master-Key": st.secrets["API_KEY"]}
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                cloud_data = response.json().get("record", {})
                if "config" in cloud_data and "data" in cloud_data:
                    return cloud_data
        except Exception as e:
            st.warning(f"云端读取失败，尝试读取本地缓存: {e}")

    if os.path.exists(LOCAL_BACKUP):
        try:
            with open(LOCAL_BACKUP, "r", encoding="utf-8") as f:
                return json.load(f)
        except: pass
    return get_default_state()

def push_to_cloud(full_data):
    try:
        with open(LOCAL_BACKUP, "w", encoding="utf-8") as f:
            json.dump(full_data, f, ensure_ascii=False, indent=2)
    except: pass

    if "BIN_ID" in st.secrets and "API_KEY" in st.secrets:
        try:
            url = f"https://api.jsonbin.io/v3/b/{st.secrets['BIN_ID']}"
            headers = {
                "Content-Type": "application/json",
                "X-Master-Key": st.secrets["API_KEY"]
            }
            requests.put(url, json=full_data, headers=headers)
        except Exception as e:
            st.error(f"云端同步失败: {e}")

if 'db' not in st.session_state:
    st.session_state.db = fetch_from_cloud()

# ==========================================
# 1. UI 美化 (CSS)
# ==========================================
def inject_custom_css():
    st.markdown("""
        <style>
        div.stButton > button:first-child[kind="primary"] {
            background-color: #07c160;
            border-color: #07c160;
            color: white;
        }
        div.stButton > button:first-child[kind="primary"]:hover {
            background-color: #05a050;
            border-color: #05a050;
        }
        .stProgress > div > div > div > div {
            background-color: #07c160;
        }
        </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. 核心数据结构
# ==========================================
class TaskNode:
    def __init__(self, name, deadline_str, start_date_str=None, subject="其他", category="日常", priority="普通"):
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

class TaskList:
    def __init__(self):
        self.head = None
        self.load_from_db()

    def sync_to_db(self):
        self.sort_by_deadline()
        data_list = []
        curr = self.head
        while curr:
            data_list.append(curr.to_dict())
            curr = curr.next

        st.session_state.db["data"] = data_list
        push_to_cloud(st.session_state.db)

    def load_from_db(self):
        data_list = st.session_state.db.get("data", [])
        self.head = None
        for item in data_list:
            self.add_node_internal(
                item.get("name"), item.get("deadline"), item.get("start_date"),
                item.get("subject", "未分类"), item.get("category", "日常"), item.get("priority", "普通")
            )

    def add_node_internal(self, name, deadline_str, start_date_str, subject, category, priority):
        new_node = TaskNode(name, deadline_str, start_date_str, subject, category, priority)
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
                self.sync_to_db()
                return "updated"
            curr = curr.next
        self.add_node_internal(name, deadline_str, None, subject, category, priority)
        self.sync_to_db()
        return "added"

    def archive_task(self, target_name):
        curr = self.head
        prev = None
        while curr:
            if curr.name == target_name:
                history_item = curr.to_dict()
                history_item["finished_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")
                if "history" not in st.session_state.db:
                    st.session_state.db["history"] = []
                st.session_state.db["history"].append(history_item)

                if prev: prev.next = curr.next
                else: self.head = curr.next

                self.sync_to_db()
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
st.set_page_config(page_title="待办事项管理系统", page_icon="✅", layout="centered")
inject_custom_css()

if 'task_list' not in st.session_state:
    st.session_state.task_list = TaskList()

# --- 侧边栏 ---
with st.sidebar:
    st.header("⚙️ 系统设置")

    with st.expander("🏷️ 标签管理", expanded=False):
        tab1, tab2 = st.tabs(["➕ 添加", "➖ 删除"])
        config_ref = st.session_state.db["config"]

        with tab1:
            n_s = st.text_input("新增领域 (如: 生活)")
            if st.button("加领域") and n_s:
                if n_s not in config_ref["subjects"]:
                    config_ref["subjects"].append(n_s)
                    push_to_cloud(st.session_state.db)
                    st.rerun()
            n_c = st.text_input("新增类型 (如: 跑腿)")
            if st.button("加类型") and n_c:
                if n_c not in config_ref["categories"]:
                    config_ref["categories"].append(n_c)
                    push_to_cloud(st.session_state.db)
                    st.rerun()
        with tab2:
            d_s = st.selectbox("删领域", ["(无)"] + config_ref["subjects"])
            if st.button("删领域") and d_s != "(无)":
                config_ref["subjects"].remove(d_s)
                push_to_cloud(st.session_state.db)
                st.rerun()
            d_c = st.selectbox("删类型", ["(无)"] + config_ref["categories"])
            if st.button("删类型") and d_c != "(无)":
                config_ref["categories"].remove(d_c)
                push_to_cloud(st.session_state.db)
                st.rerun()

# --- 主界面 ---
st.title("✅ 待办事项管理系统")
st.caption("Release Version 3.0 | 实时倒计时 | 云端同步")

# --- 发布区 ---
with st.container(border=True):
    st.subheader("📢 添加新任务")
    name = st.text_input("任务内容", placeholder="例如：拿快递、写周报、买牛奶...")
    c1, c2 = st.columns(2)
    subj = c1.selectbox("所属领域", st.session_state.db["config"]["subjects"])
    cat = c2.selectbox("任务类型", st.session_state.db["config"]["categories"])

    c3, c4, c5 = st.columns([2, 2, 1.5])
    d = c3.date_input("截止日期", min_value=datetime.now())
    t = c4.time_input("截止时间", value=datetime.strptime("23:59", "%H:%M").time())
    p = c5.select_slider("优先级", ["🟢 普通", "🟠 重要", "🔴 紧急"])

    if st.button("🚀 立即添加", use_container_width=True, type="primary"):
        if name:
            dt = datetime.combine(d, t).strftime("%Y-%m-%d %H:%M")
            p_val = p.split(" ")[1]
            st.session_state.task_list.add_or_update(name, dt, subj, cat, p_val)
            st.toast("添加成功，已同步至云端！")
            time.sleep(0.5)
            st.rerun()

st.divider()

# --- 列表显示区 ---
@st.fragment(run_every=1)
def show_list():
    now = datetime.now() # 彻底移除模拟时间，直接获取真实系统时间
    tasks = st.session_state.task_list.get_all_data()

    if not tasks:
        st.success("🎉 太棒了！当前没有任何待办任务！")
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
            d_left, h, m, s = int(left//86400), int((left%86400)//3600), int((left%3600)//60), int(left%60)
            if d_left > 0: status = f"🔵 剩 {d_left}天 {h}时"
            elif h > 0: status = f"🟠 剩 {h}时 {m}分"
            else: status = f"⚡ 仅剩 {m}分 {s}秒"

        # 样式 (泛化颜色分配，防止新的标签没有颜色)
        subj_colors = {"学习": "blue", "工作": "green", "生活": "orange", "社团": "red"}
        s_color = subj_colors.get(task.subject, "gray")
        p_icon = "🔥" if task.priority == "紧急" else ("⭐" if task.priority == "重要" else "")

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
                    s_list = st.session_state.db["config"]["subjects"]
                    c_list = st.session_state.db["config"]["categories"]
                    curr_s_idx = s_list.index(task.subject) if task.subject in s_list else 0
                    curr_c_idx = c_list.index(task.category) if task.category in c_list else 0
                    new_s = st.selectbox("修正领域", s_list, index=curr_s_idx, key=f"s_{i}")
                    new_c = st.selectbox("修正类型", c_list, index=curr_c_idx, key=f"c_{i}")

                    if st.button("💾 保存", key=f"sv_{i}"):
                        st.session_state.task_list.add_or_update(new_n, task.deadline, new_s, new_c, task.priority)
                        st.rerun()
                    if st.button("✅ 完成并归档", key=f"fin_{i}", type="primary"):
                        st.session_state.task_list.archive_task(task.name)
                        st.balloons()
                        st.toast("任务已完成并归档！")
                        time.sleep(1)
                        st.rerun()

show_list()

# --- 历史归档区 ---
with st.expander("📜 历史归档 (已完成)"):
    history_data = st.session_state.db.get("history", [])
    if history_data:
        display_data = []
        for h in reversed(history_data):
            display_data.append({
                "任务名称": h.get("name"),
                "领域": h.get("subject"),
                "完成时间": h.get("finished_at")
            })
        st.dataframe(display_data, use_container_width=True)
    else:
        st.write("暂无历史数据")