"""题库导入工具 - 支持 CSV/JSON 批量导入到数据库"""
import csv
import json
import sys
from pathlib import Path
from db_models import init_db, SessionLocal, QuestionDB
from services.question_bank import QUESTION_BANK  # 默认题库

def import_from_csv(csv_path: str):
    """从CSV导入题库

    CSV格式:
    id,knowledge_point_id,subject,content,options,correct_answer,explanation,difficulty,hint_level1,hint_level2,hint_level3
    q1,kp_math_01,数学,2x+5=13，x=?,["3","4","5","6"],4,2x=8→x=4,0.3,移项得2x=8,两边除以2,x=4
    """
    db = SessionLocal()
    count = 0

    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            options = json.loads(row['options']) if row.get('options') else None

            q = QuestionDB(
                id=row['id'],
                knowledge_point_id=row['knowledge_point_id'],
                subject=row['subject'],
                content=row['content'],
                options=options,
                correct_answer=row['correct_answer'],
                explanation=row.get('explanation', ''),
                difficulty=float(row.get('difficulty', 0.5)),
                hint_level1=row.get('hint_level1', ''),
                hint_level2=row.get('hint_level2', ''),
                hint_level3=row.get('hint_level3', '')
            )
            db.merge(q)
            count += 1

    db.commit()
    db.close()
    print(f"✅ 从CSV导入 {count} 道题目")

def import_from_json(json_path: str):
    """从JSON导入题库

    JSON格式:
    [
      {
        "id": "q1",
        "knowledge_point_id": "kp_math_01",
        "subject": "数学",
        "content": "2x+5=13，x=?",
        "options": ["3","4","5","6"],
        "correct_answer": "4",
        "explanation": "...",
        "difficulty": 0.3,
        "hint_level1": "...",
        "hint_level2": "...",
        "hint_level3": "..."
      }
    ]
    """
    db = SessionLocal()

    with open(json_path, 'r', encoding='utf-8') as f:
        questions = json.load(f)

    for q_data in questions:
        q = QuestionDB(**q_data)
        db.merge(q)

    db.commit()
    db.close()
    print(f"✅ 从JSON导入 {len(questions)} 道题目")

def import_default_questions():
    """导入默认内置题库到数据库"""
    db = SessionLocal()

    for q in QUESTION_BANK:
        q_db = QuestionDB(
            id=q.id,
            knowledge_point_id=q.knowledge_point_id,
            subject="",  # 从KNOWLEDGE_POINTS获取
            content=q.content,
            options=q.options,
            correct_answer=q.correct_answer,
            explanation=q.explanation,
            difficulty=q.difficulty,
            hint_level1=q.hint_level1,
            hint_level2=q.hint_level2,
            hint_level3=q.hint_level3
        )
        db.merge(q_db)

    db.commit()
    db.close()
    print(f"✅ 导入默认 {len(QUESTION_BANK)} 道题目到数据库")

def export_to_json(output_path: str):
    """导出数据库题库到JSON"""
    db = SessionLocal()
    rows = db.query(QuestionDB).all()

    questions = []
    for r in rows:
        questions.append({
            "id": r.id,
            "knowledge_point_id": r.knowledge_point_id,
            "subject": r.subject,
            "content": r.content,
            "options": r.options,
            "correct_answer": r.correct_answer,
            "explanation": r.explanation,
            "difficulty": r.difficulty,
            "hint_level1": r.hint_level1,
            "hint_level2": r.hint_level2,
            "hint_level3": r.hint_level3
        })

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(questions, f, ensure_ascii=False, indent=2)

    db.close()
    print(f"✅ 导出 {len(questions)} 道题目到 {output_path}")

if __name__ == "__main__":
    init_db()

    if len(sys.argv) < 2:
        print("用法:")
        print("  python import_questions.py default          # 导入内置题库")
        print("  python import_questions.py csv <文件路径>    # 从CSV导入")
        print("  python import_questions.py json <文件路径>   # 从JSON导入")
        print("  python import_questions.py export <输出路径> # 导出到JSON")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "default":
        import_default_questions()
    elif cmd == "csv" and len(sys.argv) >= 3:
        import_from_csv(sys.argv[2])
    elif cmd == "json" and len(sys.argv) >= 3:
        import_from_json(sys.argv[2])
    elif cmd == "export" and len(sys.argv) >= 3:
        export_to_json(sys.argv[2])
    else:
        print("未知命令")
