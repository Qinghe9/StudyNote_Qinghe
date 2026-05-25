"""
内存数据库 - 模拟持久化存储
支持事件溯源回放
"""

from typing import Dict, List, Optional
from models.schemas import Student, Question, Mastery, Submission, ReviewSchedule
from events.event_bus import Event, event_bus


class InMemoryDB:
    """
    内存数据库
    通过事件溯源保证数据一致性
    """

    def __init__(self):
        self._students: Dict[str, Student] = {}
        self._questions: Dict[str, Question] = {}
        self._mastery: Dict[str, Mastery] = {}  # key: student_id:topic
        self._submissions: Dict[str, List[Submission]] = {}  # key: student_id
        self._schedules: Dict[str, List[ReviewSchedule]] = {}  # key: student_id

        # 初始化示例数据
        self._init_sample_data()

    def _init_sample_data(self):
        """初始化示例题目"""
        sample_questions = [
            Question(
                question_id="q1",
                content="求解方程: 2x + 4 = 10",
                correct_answer="3",
                difficulty="easy",
                subject="数学",
                topic="一元一次方程",
                hints=[
                    "提示1: 先将常数项移到等式右边",
                    "提示2: 两边同时减去4",
                    "提示3: 2x = 6, 所以 x = 3"
                ],
                explanation="移项得 2x = 10 - 4 = 6，所以 x = 3"
            ),
            Question(
                question_id="q2",
                content="计算: 3² + 4² = ?",
                correct_answer="25",
                difficulty="easy",
                subject="数学",
                topic="幂运算",
                hints=[
                    "提示1: 先计算 3 的平方",
                    "提示2: 3² = 9, 4² = 16",
                    "提示3: 9 + 16 = 25"
                ],
                explanation="3² = 9, 4² = 16, 9 + 16 = 25"
            ),
            Question(
                question_id="q3",
                content="求导: f(x) = x³",
                correct_answer="3x²",
                difficulty="medium",
                subject="数学",
                topic="微积分",
                hints=[
                    "提示1: 使用幂函数求导法则",
                    "提示2: (x^n)' = n * x^(n-1)",
                    "提示3: 这里 n = 3"
                ],
                explanation="根据幂函数求导法则，(x³)' = 3x²"
            ),
            Question(
                question_id="q4",
                content="Python中，列表推导式 [x*2 for x in range(3)] 的结果是?",
                correct_answer="[0, 2, 4]",
                difficulty="medium",
                subject="编程",
                topic="列表推导式",
                hints=[
                    "提示1: range(3) 生成 0, 1, 2",
                    "提示2: 每个元素乘以2",
                    "提示3: 结果是 [0*2, 1*2, 2*2]"
                ],
                explanation="range(3) → [0,1,2]，每个乘2 → [0,2,4]"
            ),
            Question(
                question_id="q5",
                content="积分: ∫ 2x dx = ?",
                correct_answer="x² + C",
                difficulty="hard",
                subject="数学",
                topic="积分",
                hints=[
                    "提示1: 使用幂函数积分法则",
                    "提示2: ∫ x^n dx = x^(n+1)/(n+1) + C",
                    "提示3: 这里可以看作 2 * ∫ x dx"
                ],
                explanation="∫ 2x dx = 2 * (x²/2) + C = x² + C"
            )
        ]

        for q in sample_questions:
            self._questions[q.question_id] = q

    # === 学生管理 ===
    def create_student(self, student: Student) -> Student:
        self._students[student.student_id] = student
        return student

    def get_student(self, student_id: str) -> Optional[Student]:
        return self._students.get(student_id)

    def update_student(self, student: Student) -> Student:
        self._students[student.student_id] = student
        return student

    # === 题目管理 ===
    def get_question(self, question_id: str) -> Optional[Question]:
        return self._questions.get(question_id)

    def get_questions_by_difficulty(self, difficulty: str) -> List[Question]:
        return [q for q in self._questions.values() if q.difficulty == difficulty]

    def get_questions_by_topic(self, topic: str) -> List[Question]:
        return [q for q in self._questions.values() if q.topic == topic]

    def get_all_questions(self) -> List[Question]:
        return list(self._questions.values())

    # === 掌握度管理 (单写者策略) ===
    def get_mastery(self, student_id: str, topic: str) -> Optional[Mastery]:
        return self._mastery.get(f"{student_id}:{topic}")

    def set_mastery(self, mastery: Mastery) -> Mastery:
        key = f"{mastery.student_id}:{mastery.topic}"
        self._mastery[key] = mastery
        return mastery

    def get_student_mastery(self, student_id: str) -> List[Mastery]:
        return [m for k, m in self._mastery.items() if k.startswith(f"{student_id}:")]

    # === 提交记录 ===
    def add_submission(self, submission: Submission):
        if submission.student_id not in self._submissions:
            self._submissions[submission.student_id] = []
        self._submissions[submission.student_id].append(submission)

    def get_submissions(self, student_id: str) -> List[Submission]:
        return self._submissions.get(student_id, [])

    def get_submissions_for_question(self, student_id: str, question_id: str) -> List[Submission]:
        subs = self._submissions.get(student_id, [])
        return [s for s in subs if s.question_id == question_id]

    # === 复习计划 ===
    def add_schedule(self, schedule: ReviewSchedule):
        if schedule.student_id not in self._schedules:
            self._schedules[schedule.student_id] = []
        self._schedules[schedule.student_id].append(schedule)

    def get_schedules(self, student_id: str) -> List[ReviewSchedule]:
        return self._schedules.get(student_id, [])

    def update_schedule(self, schedule: ReviewSchedule):
        schedules = self._schedules.get(schedule.student_id, [])
        for i, s in enumerate(schedules):
            if s.schedule_id == schedule.schedule_id:
                schedules[i] = schedule
                break

    # === 事件溯源回放 ===
    def replay_events(self, events: List[Event]):
        """从事件日志重建状态"""
        print("[DB] 开始事件溯源回放...")
        for event in events:
            payload = event.payload
            if event.event_type == "STUDENT_CREATED":
                student = Student(**payload)
                self.create_student(student)
            elif event.event_type == "MASTERY_UPDATED":
                mastery = Mastery(**payload)
                self.set_mastery(mastery)
            elif event.event_type == "SUBMISSION_RECORDED":
                sub = Submission(**payload)
                self.add_submission(sub)
        print("[DB] 事件回放完成")


# 全局数据库实例
db = InMemoryDB()
