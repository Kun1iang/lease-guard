"""Deterministic rental-contract risk rules."""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass


@dataclass
class RuleMatch:
    rule_id: str
    category: str
    title: str
    severity: str
    summary: str
    impact: str
    suggestion: str
    quote: str
    page_no: int
    evidence_kind: str = "exact"
    legal_basis_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class Rule:
    rule_id: str
    category: str
    title: str
    severity: str
    summary: str
    impact: str
    suggestion: str
    detector: Callable[[str], tuple[str, int, str] | None]
    legal_basis_ids: tuple[str, ...] = ()


def _sentence(text: str, keyword: str) -> str:
    parts = re.split(r"(?<=[。！？；])|\n+", text)
    for part in parts:
        if keyword in part and part.strip():
            return part.strip()[:500]
    return text.strip()[:500]


def _page_for_text(pages: list[dict], keyword: str) -> int:
    for page in pages:
        if keyword in page["text"]:
            return int(page["page_no"])
    return int(pages[0]["page_no"]) if pages else 1


def _contains(pattern: str, text: str) -> bool:
    return bool(re.search(pattern, text))


def _match_presence(
    text: str,
    pages: list[dict],
    *,
    trigger: str,
    missing_pattern: str,
    absence_text: str,
) -> tuple[str, int, str] | None:
    if trigger not in text:
        return None
    if _contains(missing_pattern, text):
        return None
    return _sentence(text, trigger), _page_for_text(pages, trigger), absence_text


def _deposit_deadline(text: str, pages: list[dict]):
    return _match_presence(
        text,
        pages,
        trigger="押金",
        missing_pattern=r"(\d+\s*(日|天|工作日)|[一二三四五六七八九十]+\s*(日|天))[^。；]{0,30}(退|返还)",
        absence_text="合同涉及押金，但没有找到明确、可计算的具体退还期限。",
    )


def _deposit_deduction(text: str, pages: list[dict]):
    if "押金" not in text:
        return None
    if not _contains(r"押金[^。；]{0,50}(扣除|扣减|不予退还)", text):
        return None
    if _contains(r"扣除[^。；]{0,80}(原因|情形|费用|损坏|欠费)", text):
        return None
    return _sentence(text, "押金"), _page_for_text(pages, "押金"), "押金扣除条件没有写具体。"


def _rent_payment(text: str, pages: list[dict]):
    if "租金" not in text:
        return None
    if _contains(r"租金[^。；]{0,80}(每月|每季|支付|日前|提前)", text):
        return None
    return _sentence(text, "租金"), _page_for_text(pages, "租金"), "合同提到租金，但支付周期或日期不够明确。"


def _utilities(text: str, pages: list[dict]):
    if not any(word in text for word in ("水费", "电费", "燃气", "物业费")):
        return None
    if _contains(r"(水费|电费|燃气|物业费)[^。；]{0,90}(由|承担|单价|按)", text):
        return None
    return (
        _sentence(text, "费"),
        _page_for_text(pages, "费"),
        "合同涉及居住费用，但承担方或计价方式不够明确。",
    )


def _repair_shifted(text: str, pages: list[dict]):
    if not _contains(r"维修[^。；]{0,40}(均由|全部由|自行承担)[^。；]{0,20}(乙方|承租方|租客)", text):
        return None
    return _sentence(text, "维修"), _page_for_text(pages, "维修"), "维修责任可能被整体转移给承租方。"


def _wear(text: str, pages: list[dict]):
    if "损坏" not in text or _contains(r"自然损耗|正常磨损", text):
        return None
    return _sentence(text, "损坏"), _page_for_text(pages, "损坏"), "没有区分自然损耗与人为损坏。"


def _early_termination(text: str, pages: list[dict]):
    if not any(word in text for word in ("提前退租", "提前解除")):
        return None
    if _contains(r"提前退租[^。；]{0,100}(通知|违约金|补偿|扣除)", text):
        return None
    return _sentence(text, "提前"), _page_for_text(pages, "提前"), "提前解约的通知期或违约责任不明确。"


def _landlord_entry(text: str, pages: list[dict]):
    if not _contains(r"(甲方|房东|出租方)[^。；]{0,60}(进入|检查)[^。；]{0,30}房屋", text):
        return None
    if _contains(r"提前[^。；]{0,20}(通知|联系|同意)", text):
        return None
    return _sentence(text, "进入"), _page_for_text(pages, "进入"), "房东进入房屋的程序不明确。"


def _sublease(text: str, pages: list[dict]):
    if not _contains(r"(不得|禁止)[^。；]{0,15}转租", text):
        return None
    return (
        _sentence(text, "转租"),
        _page_for_text(pages, "转租"),
        "转租被完全禁止，可能限制租期变化时的处理空间。",
    )


def _auto_renew(text: str, pages: list[dict]):
    if "自动续租" not in text and "自动续期" not in text:
        return None
    return _sentence(text, "自动"), _page_for_text(pages, "自动"), "合同可能自动续期，需要确认退出方式。"


def _handover(text: str, pages: list[dict]):
    if any(word in text for word in ("交接", "物品清单", "家电清单")):
        return None
    return "", _page_for_text(pages, "房屋"), "合同中未找到明确的房屋和物品交接清单。"


def _dispute(text: str, pages: list[dict]):
    if any(word in text for word in ("争议", "诉讼", "仲裁", "法院")):
        return None
    return "", _page_for_text(pages, "合同"), "合同中未找到明确的争议解决方式。"


def _blank_fields(text: str, pages: list[dict]):
    if not _contains(r"_{3,}|待填|空白", text):
        return None
    return _sentence(text, "_"), _page_for_text(pages, "_"), "合同仍存在空白或待填写内容。"


def _rent_increase(text: str, pages: list[dict]):
    if not _contains(
        r"(甲方|出租方)[^。；]{0,30}(有权|可以)[^。；]{0,20}(调整|提高|上涨)[^。；]{0,10}租金", text
    ):
        return None
    return _sentence(text, "租金"), _page_for_text(pages, "租金"), "出租方可能保留单方面调整租金的权利。"


def _deposit_amount(text: str, pages: list[dict]):
    match = re.search(r"押金[^。；]{0,40}([2-9]|十|[一二两三四五六七八九])个月[^。；]{0,10}租金", text)
    if not match:
        return None
    return _sentence(text, "押金"), _page_for_text(pages, "押金"), "押金金额较高，需要确认退还和扣除规则。"


def _notice_period(text: str, pages: list[dict]):
    if "通知" not in text:
        return None
    if _contains(r"(提前|至少)\s*\d+\s*(日|天)", text):
        return None
    return _sentence(text, "通知"), _page_for_text(pages, "通知"), "合同提到通知，但没有明确通知期。"


RULES: tuple[Rule, ...] = (
    Rule(
        "DEPOSIT_DEADLINE",
        "deposit",
        "押金退还期限不明确",
        "high",
        "合同没有写明可计算的押金退还期限。",
        "退房后可能长期无法确认押金何时到账。",
        "建议约定交接完成后的具体退还天数和逾期处理。",
        _deposit_deadline,
        ("kb_civil_lease",),
    ),
    Rule(
        "DEPOSIT_DEDUCTION",
        "deposit",
        "押金扣除条件过宽",
        "high",
        "押金可能被扣除，但条件不够具体。",
        "房东可能扩大扣除范围。",
        "逐项写明可扣除费用、凭证和剩余金额退还时间。",
        _deposit_deduction,
        ("kb_civil_lease",),
    ),
    Rule(
        "RENT_PAYMENT",
        "rent",
        "租金支付规则不明确",
        "medium",
        "租金支付周期或日期不够明确。",
        "可能造成逾期争议。",
        "写明每月支付日、支付方式和逾期处理。",
        _rent_payment,
        ("kb_civil_lease",),
    ),
    Rule(
        "UTILITY_COST",
        "fees",
        "居住费用承担不明确",
        "medium",
        "水电燃气或物业费用的承担方式不明确。",
        "退租时可能出现额外费用争议。",
        "列明费用项目、承担方、计价方式和结算周期。",
        _utilities,
        ("kb_risk_fees",),
    ),
    Rule(
        "REPAIR_SHIFTED",
        "maintenance",
        "维修责任全部转移",
        "high",
        "维修责任可能整体由承租方承担。",
        "非租客原因造成的维修也可能产生费用。",
        "区分房屋主体与设施自然损坏、人为损坏，并约定响应时限。",
        _repair_shifted,
        ("kb_civil_repair",),
    ),
    Rule(
        "WEAR_VS_DAMAGE",
        "maintenance",
        "未区分自然损耗与人为损坏",
        "medium",
        "合同只写“损坏”，没有排除自然损耗。",
        "正常使用后的磨损可能被要求赔偿。",
        "增加自然损耗免责和交接验收标准。",
        _wear,
        ("kb_civil_repair",),
    ),
    Rule(
        "EARLY_TERMINATION",
        "termination",
        "提前解约责任不明确",
        "high",
        "提前退租的通知期或违约责任不明确。",
        "临时退租时责任和赔偿可能无法预期。",
        "写明通知期、违约金计算方式和押金处理。",
        _early_termination,
        ("kb_civil_lease",),
    ),
    Rule(
        "LANDLORD_ENTRY",
        "privacy",
        "房东入户程序不明确",
        "high",
        "房东进入房屋的提前通知和条件不明确。",
        "居住安宁和隐私可能受到影响。",
        "约定非紧急情况下需提前通知并征得合理同意。",
        _landlord_entry,
        ("kb_civil_lease",),
    ),
    Rule(
        "SUBLEASE_BAN",
        "sublease",
        "转租被完全禁止",
        "medium",
        "合同禁止任何形式的转租。",
        "工作或生活变化时可能增加解约成本。",
        "确认是否允许经书面同意的转租或换租。",
        _sublease,
        ("kb_civil_sublease",),
    ),
    Rule(
        "AUTO_RENEW",
        "renewal",
        "合同可能自动续租",
        "high",
        "合同包含自动续租或续期约定。",
        "忘记提出不续租时可能被动进入下一租期。",
        "写明续租选择方式和最晚提出不续租的时间。",
        _auto_renew,
        ("kb_civil_lease",),
    ),
    Rule(
        "HANDOVER_LIST",
        "handover",
        "缺少物品交接清单",
        "medium",
        "未发现明确的房屋和物品交接清单。",
        "退租时可能对物品状态产生争议。",
        "在入住前共同拍照并列出家具家电状态。",
        _handover,
        ("kb_risk_handover",),
    ),
    Rule(
        "DISPUTE_RESOLUTION",
        "dispute",
        "争议解决方式缺失",
        "medium",
        "合同未明确争议处理路径。",
        "发生纠纷时可能增加沟通成本。",
        "约定协商、调解、诉讼或仲裁的具体路径。",
        _dispute,
        ("kb_civil_lease",),
    ),
    Rule(
        "BLANK_FIELD",
        "text",
        "合同存在空白字段",
        "high",
        "合同包含空白或未填写内容。",
        "空白处可能在后续被补写。",
        "签约前划掉所有空白，并保留双方确认后的完整版本。",
        _blank_fields,
        ("kb_risk_blank",),
    ),
    Rule(
        "RENT_INCREASE",
        "rent",
        "单方涨租空间过宽",
        "high",
        "出租方可能保留单方面调整租金的权利。",
        "租期内成本可能超出预期。",
        "约定租期内租金固定，续租调整需双方书面同意。",
        _rent_increase,
        ("kb_civil_lease",),
    ),
    Rule(
        "DEPOSIT_AMOUNT",
        "deposit",
        "押金金额较高",
        "medium",
        "押金金额需要进一步确认。",
        "一次性资金压力较大。",
        "确认当地常见水平和退还条件，并写入合同。",
        _deposit_amount,
        ("kb_risk_deposit",),
    ),
    Rule(
        "NOTICE_PERIOD",
        "termination",
        "通知期不明确",
        "medium",
        "合同提到通知但没有明确提前时间。",
        "双方可能对通知是否充分产生争议。",
        "将通知方式和天数写成可计算条款。",
        _notice_period,
        ("kb_civil_lease",),
    ),
)


def evaluate_rules(pages: list[dict]) -> list[RuleMatch]:
    text = "\n".join(str(page["text"]) for page in pages)
    matches: list[RuleMatch] = []
    for rule in RULES:
        detected = rule.detector(text, pages)
        if not detected:
            continue
        quote, page_no, _ = detected
        kind = "exact" if quote else "absence"
        matches.append(
            RuleMatch(
                rule_id=rule.rule_id,
                category=rule.category,
                title=rule.title,
                severity=rule.severity,
                summary=rule.summary,
                impact=rule.impact,
                suggestion=rule.suggestion,
                quote=quote,
                page_no=page_no,
                evidence_kind=kind,
                legal_basis_ids=rule.legal_basis_ids,
            )
        )
    return matches
