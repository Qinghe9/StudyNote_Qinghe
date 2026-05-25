"""
SM-2 间隔重复算法实现
根据学习者表现动态调整复习间隔
"""

from datetime import datetime, timedelta
from typing import Optional
from models.schemas import Mastery


class SM2Algorithm:
    """
    SuperMemo-2 算法实现

    核心逻辑:
    - 质量评分(0-5): 0=完全错误, 3=正确但困难, 5=完美回答
    - 轻松因子(EF): 初始2.5, 根据表现调整
    - 间隔递增: 成功则间隔增长, 失败则重置
    """

    MIN_EASE_FACTOR = 1.3

    @staticmethod
    def calculate_next_review(mastery: Mastery, quality: int) -> Mastery:
        """
        计算下一次复习时间

        Args:
            mastery: 当前掌握度状态
            quality: 回忆质量 0-5

        Returns:
            更新后的掌握度状态
        """
        if quality < 0 or quality > 5:
            quality = max(0, min(5, quality))

        # 更新版本号(乐观锁)
        mastery.version += 1

        if quality < 3:
            # 回忆失败 - 重置间隔
            mastery.repetitions = 0
            mastery.interval_days = 1
            mastery.level = max(0, mastery.level - 0.2)
        else:
            # 回忆成功 - 递增间隔
            mastery.repetitions += 1
            mastery.level = min(1.0, mastery.level + 0.1 * (quality / 5))

            if mastery.repetitions == 1:
                mastery.interval_days = 1
            elif mastery.repetitions == 2:
                mastery.interval_days = 6
            else:
                # interval = interval * ease_factor
                mastery.interval_days = int(mastery.interval_days * mastery.ease_factor)

        # 更新轻松因子
        mastery.ease_factor = max(
            SM2Algorithm.MIN_EASE_FACTOR,
            mastery.ease_factor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
        )

        # 设置下次复习时间
        mastery.last_reviewed = datetime.now().isoformat()
        next_date = datetime.now() + timedelta(days=mastery.interval_days)
        mastery.next_review = next_date.isoformat()

        return mastery

    @staticmethod
    def get_quality_from_correctness(is_correct: bool, time_spent: int, expected_time: int = 60) -> int:
        """
        根据答题情况推断质量评分

        Args:
            is_correct: 是否正确
            time_spent: 耗时(秒)
            expected_time: 预期耗时(秒)

        Returns:
            质量评分 0-5
        """
        if not is_correct:
            return 0  # 完全错误

        # 根据耗时调整质量
        ratio = time_spent / expected_time
        if ratio < 0.5:
            return 5  # 非常快且正确
        elif ratio < 0.8:
            return 4  # 较快且正确
        elif ratio < 1.2:
            return 3  # 正常速度
        elif ratio < 2.0:
            return 2  # 较慢
        else:
            return 1  # 非常慢(勉强正确)

    @staticmethod
    def is_due_for_review(mastery: Mastery) -> bool:
        """检查是否到了复习时间"""
        if not mastery.next_review:
            return True

        next_date = datetime.fromisoformat(mastery.next_review)
        return datetime.now() >= next_date
