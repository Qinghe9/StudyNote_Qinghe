#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
智能表单输入提示与验证系统：朴素贝叶斯密码强度模型训练脚本

本版本只兼容 Kaggle 下载的 password_password_data.csv，不再依赖 password_samples.csv。

要求数据文件位置：

smart_form_nb_experiment/
├─ data/
│  └─ password_data.csv
├─ model/
└─ train/
   └─ train_password_nb.py

password_data.csv 格式示例：

password,strength
kzde5577,1
kino3434,1
visi7k1yr,1
megzy123,1
lamborghin1,1
AVYq1lDE4MgAZfNt,2

标签说明：

0 -> weak
1 -> medium
2 -> strong

运行命令：

python train/train_password_nb.py
"""

from pathlib import Path
import csv
import json
import math
import random
from collections import Counter


PROJECT_ROOT = Path(__file__).resolve().parents[1]

# 只读取 Kaggle 数据集
DATA_PATH = PROJECT_ROOT / "data" / "password_data.csv"

# 输出模型文件，前端 js/app.js 会读取这个文件
MODEL_PATH = PROJECT_ROOT / "model" / "password_nb_model.json"

# 是否限制读取样本数量
# 课堂实验建议先设为 50000，训练更快
# 如果想使用全部数据，可以改成 None
MAX_ROWS = 50000

# 测试集比例
TEST_RATIO = 0.2

# 固定随机种子，保证每次划分结果一致
RANDOM_SEED = 42

CLASSES = ["weak", "medium", "strong"]

LABEL_MAP = {
    "0": "weak",
    "1": "medium",
    "2": "strong"
}

COMMON_WEAK_WORDS = {
    "password",
    "admin",
    "qwerty",
    "abc",
    "test",
    "student",
    "user",
    "letmein",
    "welcome",
    "iloveyou"
}

KEYBOARD_PATTERNS = [
    "qwerty",
    "asdf",
    "zxcv",
    "qaz",
    "wsx",
    "1234",
    "abcd"
]


def has_sequence(text):
    """
    判断是否存在连续递增或递减字符。
    例如：abc、cba、123、321。
    """
    text = (text or "").lower()

    for i in range(len(text) - 2):
        a = ord(text[i])
        b = ord(text[i + 1])
        c = ord(text[i + 2])

        if b == a + 1 and c == b + 1:
            return True

        if b == a - 1 and c == b - 1:
            return True

    return False


def has_repeated(text):
    """
    判断是否存在同一字符连续出现 3 次及以上。
    例如：aaa、111、xxx。
    """
    text = text or ""

    for i in range(len(text) - 2):
        if text[i] == text[i + 1] == text[i + 2]:
            return True

    return False


def extract_features(password):
    """
    将密码转换为朴素贝叶斯可使用的离散特征。

    注意：
    这里的特征提取逻辑要和前端 js/app.js 保持一致。
    否则 Python 训练出来的模型和前端预测时使用的特征不一致，会影响网页端预测结果。
    """
    p = str(password or "")
    lower = p.lower()
    length = len(p)

    if length < 8:
        len_bucket = "short"
    elif length <= 11:
        len_bucket = "medium"
    else:
        len_bucket = "long"

    has_lower = any(ch.islower() for ch in p)
    has_upper = any(ch.isupper() for ch in p)
    has_digit = any(ch.isdigit() for ch in p)
    has_symbol = any(not ch.isalnum() for ch in p)

    categories = sum([
        has_lower,
        has_upper,
        has_digit,
        has_symbol
    ])

    if categories <= 1:
        mix_bucket = "single"
    elif categories == 2:
        mix_bucket = "double"
    elif categories == 3:
        mix_bucket = "triple"
    else:
        mix_bucket = "quad"

    contains_common = any(word in lower for word in COMMON_WEAK_WORDS)
    keyboard = any(pattern in lower for pattern in KEYBOARD_PATTERNS)
    year_like = any(str(y) in p for y in range(1990, 2031))

    return [
        f"len={len_bucket}",
        f"mix={mix_bucket}",
        f"lower={'yes' if has_lower else 'no'}",
        f"upper={'yes' if has_upper else 'no'}",
        f"digit={'yes' if has_digit else 'no'}",
        f"symbol={'yes' if has_symbol else 'no'}",
        f"common={'yes' if contains_common else 'no'}",
        f"repeat={'yes' if has_repeated(p) else 'no'}",
        f"sequence={'yes' if has_sequence(p) else 'no'}",
        f"keyboard={'yes' if keyboard else 'no'}",
        f"year={'yes' if year_like else 'no'}",
    ]


def normalize_row(row):
    """
    处理 CSV 行数据。

    有些 CSV 可能存在 BOM 或字段名前后空格，所以这里统一清洗字段名。
    """
    clean_row = {}

    for key, value in row.items():
        if key is None:
            continue

        clean_key = key.replace("\ufeff", "").strip()
        clean_row[clean_key] = value

    return clean_row


def normalize_label(value):
    """
    将 Kaggle 的 strength 标签转换为 weak / medium / strong。
    """
    if value is None:
        return None

    value = str(value).strip()

    return LABEL_MAP.get(value)


def read_dataset():
    """
    读取 Kaggle 数据集 data/password_data.csv。

    必须包含两个字段：
    password,strength
    """
    if not DATA_PATH.exists():
        raise FileNotFoundError(
            f"没有找到数据集文件：{DATA_PATH}\n"
            f"请把 Kaggle 下载的 password_data.csv 放到 data/password_data.csv。"
        )

    rows = []

    with DATA_PATH.open("r", encoding="utf-8", errors="ignore", newline="") as f:
        reader = csv.DictReader(f)

        if not reader.fieldnames:
            raise ValueError("password_data.csv 文件为空，无法读取字段名。")

        fieldnames = [
            name.replace("\ufeff", "").strip()
            for name in reader.fieldnames
            if name is not None
        ]

        print("读取到字段：", fieldnames)

        if "password" not in fieldnames or "strength" not in fieldnames:
            raise ValueError(
                "password_data.csv 字段不符合要求。必须包含 password 和 strength 两列。"
            )

        for row in reader:
            if MAX_ROWS is not None and len(rows) >= MAX_ROWS:
                break

            row = normalize_row(row)

            password = row.get("password")
            strength = row.get("strength")

            if password is None or strength is None:
                continue

            password = str(password).strip()
            label = normalize_label(strength)

            if not password:
                continue

            if label not in CLASSES:
                continue

            rows.append((password, label))

    if not rows:
        raise ValueError(
            "没有读取到有效数据，请检查 password_data.csv 是否为 password,strength 格式。"
        )

    return rows


def split_train_test(rows):
    """
    按类别分层划分训练集和测试集。

    这样可以避免随机划分后某一类样本太少，导致测试结果不稳定。
    """
    random.seed(RANDOM_SEED)

    grouped = {
        label: []
        for label in CLASSES
    }

    for password, label in rows:
        grouped[label].append((password, label))

    train_rows = []
    test_rows = []

    for label, items in grouped.items():
        random.shuffle(items)

        if len(items) <= 1:
            train_rows.extend(items)
            continue

        test_size = max(1, int(len(items) * TEST_RATIO))

        test_rows.extend(items[:test_size])
        train_rows.extend(items[test_size:])

    random.shuffle(train_rows)
    random.shuffle(test_rows)

    return train_rows, test_rows


def train_naive_bayes(rows, alpha=1.0):
    """
    训练多分类朴素贝叶斯模型。
    """
    class_counts = Counter(label for _, label in rows)

    token_counts = {
        label: Counter()
        for label in CLASSES
    }

    total_tokens = {
        label: 0
        for label in CLASSES
    }

    vocabulary = set()

    for password, label in rows:
        tokens = extract_features(password)

        token_counts[label].update(tokens)
        total_tokens[label] += len(tokens)
        vocabulary.update(tokens)

    n_samples = len(rows)
    n_classes = len(CLASSES)

    priors = {}

    for label in CLASSES:
        priors[label] = (
            class_counts[label] + alpha
        ) / (
            n_samples + alpha * n_classes
        )

    vocab_size = len(vocabulary)
    likelihoods = {}

    for label in CLASSES:
        likelihoods[label] = {}

        denominator = total_tokens[label] + alpha * vocab_size

        for token in vocabulary:
            likelihoods[label][token] = (
                token_counts[label][token] + alpha
            ) / denominator

    return {
        "classes": CLASSES,
        "priors": priors,
        "likelihoods": likelihoods,
        "vocabulary": sorted(vocabulary),
        "alpha": alpha,
        "feature_version": "frontend_compatible_v1"
    }


def predict(model, password):
    """
    使用训练好的朴素贝叶斯模型预测密码强度。
    """
    tokens = extract_features(password)
    unknown_prob = 1.0 / (len(model["vocabulary"]) + 100)
    scores = {}

    for label in model["classes"]:
        score = math.log(model["priors"][label])

        for token in tokens:
            score += math.log(
                model["likelihoods"][label].get(token, unknown_prob)
            )

        scores[label] = score

    return max(scores, key=scores.get)


def evaluate(model, test_rows):
    """
    评估模型准确率，并生成混淆矩阵。
    """
    if not test_rows:
        return 0, {}

    correct = 0

    confusion = {
        true_label: {
            pred_label: 0
            for pred_label in CLASSES
        }
        for true_label in CLASSES
    }

    for password, true_label in test_rows:
        pred_label = predict(model, password)

        if pred_label == true_label:
            correct += 1

        confusion[true_label][pred_label] += 1

    accuracy = correct / len(test_rows)

    return accuracy, confusion


def print_dataset_info(rows):
    """
    打印数据集基本情况。
    """
    label_counts = Counter(label for _, label in rows)

    print("\n数据集统计：")
    print(f"总样本数：{len(rows)}")

    for label in CLASSES:
        print(f"{label}: {label_counts[label]}")


def print_confusion_matrix(confusion):
    """
    打印简单混淆矩阵。
    """
    print("\n混淆矩阵：")
    print("真实标签 \\ 预测标签".ljust(18), end="")

    for pred_label in CLASSES:
        print(pred_label.rjust(10), end="")

    print()

    for true_label in CLASSES:
        print(true_label.ljust(18), end="")

        for pred_label in CLASSES:
            print(str(confusion[true_label][pred_label]).rjust(10), end="")

        print()


def main():
    print("开始读取 Kaggle 密码强度数据集 data/password_data.csv ...")

    rows = read_dataset()
    print_dataset_info(rows)

    train_rows, test_rows = split_train_test(rows)

    print("\n训练集样本数：", len(train_rows))
    print("测试集样本数：", len(test_rows))

    model_for_eval = train_naive_bayes(train_rows)
    accuracy, confusion = evaluate(model_for_eval, test_rows)

    print("\n测试集准确率：", round(accuracy, 4))
    print_confusion_matrix(confusion)

    final_model = train_naive_bayes(rows)

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    MODEL_PATH.write_text(
        json.dumps(final_model, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print("\n模型已导出：", MODEL_PATH)
    print("前端页面会读取该文件：model/password_nb_model.json")


if __name__ == "__main__":
    main()