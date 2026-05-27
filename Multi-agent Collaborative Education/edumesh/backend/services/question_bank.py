"""题库数据"""
from models.student import Question

QUESTION_BANK = [
    Question(
        id="q1",
        knowledge_point_id="kp_math_01",
        content="如果 2x + 5 = 13，那么 x 的值是多少？",
        options=["3", "4", "5", "6"],
        correct_answer="4",
        explanation="2x = 13 - 5 = 8，所以 x = 4",
        difficulty=0.3,
        hint_level1="试着把5移到等式右边。",
        hint_level2="移项后得到 2x = 8，接下来怎么做？",
        hint_level3="两边同时除以2，x = 8/2 = 4。"
    ),
    Question(
        id="q2",
        knowledge_point_id="kp_math_01",
        content="解方程: 3(x - 2) = 9",
        options=["3", "5", "6", "9"],
        correct_answer="5",
        explanation="3x - 6 = 9 → 3x = 15 → x = 5",
        difficulty=0.5,
        hint_level1="先展开括号。",
        hint_level2="展开后得到 3x - 6 = 9，然后移项。",
        hint_level3="3x = 15，x = 5。"
    ),
    Question(
        id="q3",
        knowledge_point_id="kp_math_02",
        content="一个三角形的底是6cm，高是4cm，面积是多少？",
        options=["10", "12", "20", "24"],
        correct_answer="12",
        explanation="面积 = 底 × 高 / 2 = 6 × 4 / 2 = 12",
        difficulty=0.4,
        hint_level1="回忆三角形面积公式。",
        hint_level2="面积 = 底 × 高 ÷ 2",
        hint_level3="6 × 4 = 24，再除以2得到12。"
    ),
    Question(
        id="q4",
        knowledge_point_id="kp_math_02",
        content="圆的半径是5cm，它的周长是多少？(π取3.14)",
        options=["15.7", "31.4", "62.8", "78.5"],
        correct_answer="31.4",
        explanation="周长 = 2πr = 2 × 3.14 × 5 = 31.4",
        difficulty=0.5,
        hint_level1="回忆圆周长公式。",
        hint_level2="周长 = 2 × π × 半径",
        hint_level3="2 × 3.14 × 5 = 31.4"
    ),
    Question(
        id="q5",
        knowledge_point_id="kp_math_03",
        content="下列哪个数是质数？",
        options=["9", "15", "17", "21"],
        correct_answer="17",
        explanation="17只能被1和17整除，是质数。9=3×3, 15=3×5, 21=3×7",
        difficulty=0.6,
        hint_level1="质数只能被1和它本身整除。",
        hint_level2="检查每个选项是否有除了1和自身以外的因数。",
        hint_level3="17不能被2,3,5,7整除，所以是质数。"
    ),
    Question(
        id="q6",
        knowledge_point_id="kp_physics_01",
        content="一个物体质量为2kg，加速度为3m/s²，根据牛顿第二定律，合力是多少？",
        options=["5N", "6N", "8N", "9N"],
        correct_answer="6",
        explanation="F = ma = 2 × 3 = 6N",
        difficulty=0.4,
        hint_level1="回忆牛顿第二定律公式。",
        hint_level2="F = m × a",
        hint_level3="2kg × 3m/s² = 6N"
    ),
    Question(
        id="q7",
        knowledge_point_id="kp_physics_01",
        content="光在真空中的速度约为多少？",
        options=["3×10⁶ m/s", "3×10⁷ m/s", "3×10⁸ m/s", "3×10⁹ m/s"],
        correct_answer="3×10⁸ m/s",
        explanation="光速 c ≈ 3 × 10⁸ m/s",
        difficulty=0.3,
        hint_level1="这是一个需要记忆的物理常数。",
        hint_level2="光速大约是每秒30万公里。",
        hint_level3="3×10⁸ m/s = 300,000,000 m/s = 300,000 km/s"
    ),
    Question(
        id="q8",
        knowledge_point_id="kp_cs_01",
        content="Python中，以下代码的输出是什么？\nprint(2 ** 3)",
        options=["6", "8", "9", "23"],
        correct_answer="8",
        explanation="** 是幂运算符，2³ = 8",
        difficulty=0.3,
        hint_level1="** 在Python中代表什么运算？",
        hint_level2="** 是幂运算，不是乘法。",
        hint_level3="2 ** 3 = 2³ = 2×2×2 = 8"
    ),
    Question(
        id="q9",
        knowledge_point_id="kp_cs_01",
        content="以下哪个不是Python的基本数据类型？",
        options=["int", "str", "array", "float"],
        correct_answer="array",
        explanation="Python基本类型: int, float, str, bool, list, dict, tuple, set。array需要import array模块",
        difficulty=0.6,
        hint_level1="想想Python内置了哪些类型。",
        hint_level2="list是内置的，array需要额外导入。",
        hint_level3="array不是Python内置基本类型，需要 import array。"
    ),
    Question(
        id="q10",
        knowledge_point_id="kp_cs_02",
        content="时间复杂度 O(n log n) 通常对应哪种算法？",
        options=["冒泡排序", "快速排序(平均)", "线性搜索", "哈希查找"],
        correct_answer="快速排序(平均)",
        explanation="快速排序平均O(n log n)，最坏O(n²)。冒泡O(n²)，线性O(n)，哈希O(1)",
        difficulty=0.7,
        hint_level1="回忆常见排序算法的时间复杂度。",
        hint_level2="归并排序和快速排序的平均复杂度都是O(n log n)。",
        hint_level3="快速排序分治策略，平均每次划分平衡时复杂度为O(n log n)。"
    ),
]

KNOWLEDGE_POINTS = {
    "kp_math_01": {"name": "一元一次方程", "subject": "数学"},
    "kp_math_02": {"name": "几何图形面积", "subject": "数学"},
    "kp_math_03": {"name": "质数与合数", "subject": "数学"},
    "kp_physics_01": {"name": "牛顿力学基础", "subject": "物理"},
    "kp_cs_01": {"name": "Python基础语法", "subject": "计算机"},
    "kp_cs_02": {"name": "算法复杂度分析", "subject": "计算机"},
}
