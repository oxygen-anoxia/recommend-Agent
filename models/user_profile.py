import json
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum

class ProfileCompleteness(Enum):
    """画像完整性状态"""
    COMPLETE = "complete"
    INCOMPLETE = "incomplete"
    MINIMAL = "minimal"

@dataclass
class UserProfile:
    """MCP版本的用户画像模型"""
    # 基本学术信息
    GPA: float = 0xffff
    SCHOOL: str = "UNKNOWN"
    GRE: int = 0xffff
    TOEFL: int = 0xffff
    ITELS: float = 0xffff

    major: str = "UNKNOWN"
    degree: str = "UNKNOWN"  # 学位类型：本科/硕士/博士/短期课程
    background_institution_rating: str = "UNKNOWN"  # 背景院校评级

    work_experience: List[str] = []   # 工作经历
    extracurricular: List[str] = []   # 课外活动

    # 研究相关
    research: List[str] = field(default_factory=list)
    if_research: bool = False

    # 目标信息
    target_major: str = "UNKNOWN"
    target_country: str = "UNKNOWN"
    region: List[str] = field(default_factory=list)  # 目标地区列表
    preferred_universities: List[str] = field(default_factory=list)  # 偏好大学列表

    # 预算和排名
    budget_max: int = 0xffff  # 最大预算
    budget_min: int = 0       # 最小预算
    rank_max: int = 0xffff    # 最大排名要求

    # 经历信息
    work_experience: List[str] = field(default_factory=list)   # 工作经历
    extracurricular: List[str] = field(default_factory=list)   # 课外活动

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return asdict(self)

    def getProfile(self) -> str:
        """获取JSON格式的画像信息，兼容原有接口"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)

    def upgradeProfile(self, update_data: Dict[str, Any]) -> List[str]:
        """更新用户画像，返回更新的字段列表"""
        updated_fields = []

        for key, value in update_data.items():
            if hasattr(self, key):
                current_value = getattr(self, key)

                # 对于列表类型的字段，进行追加而不是覆盖
                if isinstance(current_value, list) and isinstance(value, list):
                    for item in value:
                        if item not in current_value:
                            current_value.append(item)
                            updated_fields.append(key)
                elif current_value != value:
                    setattr(self, key, value)
                    updated_fields.append(key)
            else:
                print(f"[警告] 尝试更新不存在的字段: {key}")

        return updated_fields

    def check_profile_completeness(self) -> Tuple[ProfileCompleteness, List[str]]:
        """检查画像完整性，返回状态和缺失字段"""
        # 定义必需字段（不能被猜测的字段）
        essential_fields = {
            "degree": self.degree,
            "major": self.major,
            "target_country": self.target_country,
            "target_major": self.target_major
        }
    
        # 定义重要字段（可以被猜测的字段）
        important_fields = {
            "GPA": self.GPA,
            "region": self.region,
            "background_institution_rating": self.background_institution_rating,
            "rank_max": self.rank_max,
            "budget_max": self.budget_max
        }
    
        missing_essential = []
        missing_important = []
    
        # 检查必需字段
        for field, value in essential_fields.items():
            if value in ["UNKNOWN", 0xffff, [], None]:
                missing_essential.append(field)
    
        # 检查重要字段
        for field, value in important_fields.items():
            if value in ["UNKNOWN", 0xffff, [], None]:
                missing_important.append(field)
    
        # 确定完整性状态
        if not missing_essential and not missing_important:
            return ProfileCompleteness.COMPLETE, []
        elif not missing_essential:
            return ProfileCompleteness.MINIMAL, missing_important
        else:
            return ProfileCompleteness.INCOMPLETE, missing_essential + missing_important

    def get_completion_summary(self) -> Dict[str, Any]:
        """获取完整性摘要"""
        completeness, missing_fields = self.check_profile_completeness()

        total_fields = 16  # 总字段数
        filled_fields = total_fields - len(missing_fields)
        completion_rate = (filled_fields / total_fields) * 100

        return {
            "status": completeness.value,
            "completion_rate": round(completion_rate, 2),
            "filled_fields": filled_fields,
            "total_fields": total_fields,
            "missing_fields": missing_fields
        }

    def __str__(self) -> str:
        completeness, _ = self.check_profile_completeness()
        return f"UserProfile(completeness={completeness.value}, major={self.major}, target_country={self.target_country})"