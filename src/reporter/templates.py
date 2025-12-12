"""Hebrew text templates for report generation."""

from src.models import ViolationType

# Hebrew violation type names
VIOLATION_TYPE_NAMES_HE = {
    ViolationType.MINIMUM_WAGE: "שכר מינימום",
    ViolationType.HOURS_RATE_MISMATCH: "חישוב שעות × תעריף",
    ViolationType.MISSING_PENSION: "הפרשות פנסיה",
    ViolationType.OVERTIME_UNDERPAID: "שעות נוספות",
    ViolationType.WEEKEND_UNDERPAID: "עבודת שבת/חג",
    ViolationType.MISSING_VACATION: "דמי חופשה",
}

# Hebrew month names
HEBREW_MONTHS = {
    1: "ינואר",
    2: "פברואר",
    3: "מרץ",
    4: "אפריל",
    5: "מאי",
    6: "יוני",
    7: "יולי",
    8: "אוגוסט",
    9: "ספטמבר",
    10: "אוקטובר",
    11: "נובמבר",
    12: "דצמבר",
}

# Report section headers
SECTION_HEADERS = {
    "title": "דוח ניתוח תלושי שכר",
    "summary": "סיכום כללי",
    "violations": "הפרות שנמצאו",
    "monthly_breakdown": "פירוט חודשי",
    "recommendations": "המלצות",
    "legal_notice": "הערה משפטית",
}

# Summary templates
SUMMARY_TEMPLATES = {
    "total_analyzed": "נותחו {count} תלושי שכר",
    "compliant": "{count} תלושים תקינים",
    "non_compliant": "{count} תלושים עם הפרות",
    "total_missing": "סך הכל חסר: {amount}",
    "compliance_rate": "שיעור תאימות: {rate}%",
}

# Risk level descriptions
RISK_LEVEL_HE = {
    "low": "סיכון נמוך",
    "medium": "סיכון בינוני",
    "high": "סיכון גבוה",
    "critical": "סיכון קריטי",
}

RISK_LEVEL_DESCRIPTIONS = {
    "low": "מצב תקין - רוב התלושים עומדים בדרישות החוק.",
    "medium": "נדרשת תשומת לב - קיימות מספר הפרות שיש לטפל בהן.",
    "high": "מצב בעייתי - הפרות משמעותיות של דיני עבודה.",
    "critical": "מצב חמור - רוב התלושים אינם עומדים בדרישות החוק.",
}

# Violation explanation templates
VIOLATION_EXPLANATIONS = {
    ViolationType.MINIMUM_WAGE: """
הפרת שכר מינימום
-----------------
שכר המינימום בישראל נקבע בחוק שכר מינימום, התשמ"ז-1987.
כל עובד זכאי לשכר שעתי שלא יפחת מהשכר המינימלי הקבוע בחוק.

בתלוש זה: שולם {actual} ש"ח לשעה
שכר מינימום לתקופה: {expected} ש"ח לשעה
הפרש לשעה: {diff_hourly} ש"ח
סה"כ חסר: {missing} ש"ח
""",
    ViolationType.HOURS_RATE_MISMATCH: """
אי התאמה בחישוב שכר
--------------------
שכר הבסיס אינו תואם את החישוב של שעות × תעריף שעתי.

שעות עבודה: {hours}
תעריף שעתי: {rate} ש"ח
חישוב צפוי: {expected} ש"ח
שכר בסיס בפועל: {actual} ש"ח
הפרש: {missing} ש"ח
""",
    ViolationType.MISSING_PENSION: """
חוסר בהפרשות פנסיה
-------------------
על פי צו ההרחבה לפנסיה חובה, כל עובד זכאי להפרשות פנסיוניות.
שיעור ההפרשה הנדרש: עובד 6%, מעביד 6.5%

שכר ברוטו: {gross} ש"ח
הפרשה נדרשת (עובד): {expected} ש"ח
הפרשה בפועל: {actual} ש"ח
חסר: {missing} ש"ח
""",
    ViolationType.OVERTIME_UNDERPAID: """
תשלום חסר בשעות נוספות
-----------------------
על פי חוק שעות עבודה ומנוחה, שעות נוספות משולמות בתעריף מוגדל:
- 2 שעות ראשונות: 125% מהשכר הרגיל
- מעבר לכך: 150% מהשכר הרגיל

שעות נוספות: {hours}
תשלום צפוי (מינימום): {expected} ש"ח
תשלום בפועל: {actual} ש"ח
חסר: {missing} ש"ח
""",
}

# Recommendation templates
RECOMMENDATIONS = {
    ViolationType.MINIMUM_WAGE: "יש לעדכן את השכר השעתי לפחות לגובה שכר המינימום החוקי.",
    ViolationType.HOURS_RATE_MISMATCH: "יש לבדוק את חישוב שכר הבסיס ולוודא התאמה בין שעות לתעריף.",
    ViolationType.MISSING_PENSION: "יש לוודא הפרשות פנסיוניות כנדרש בחוק.",
    ViolationType.OVERTIME_UNDERPAID: "יש לחשב מחדש את תשלום השעות הנוספות לפי התעריפים החוקיים.",
    ViolationType.WEEKEND_UNDERPAID: "יש לוודא תשלום תוספת שבת/חג כנדרש בחוק.",
    ViolationType.MISSING_VACATION: "יש לבדוק את זכויות החופשה השנתית.",
}

# Legal notice
LEGAL_NOTICE = """
הערה משפטית חשובה
==================
דוח זה נועד לסייע בזיהוי חריגות אפשריות מדיני העבודה בישראל.
הדוח אינו מהווה ייעוץ משפטי ואינו מחליף התייעצות עם עורך דין.

במקרה של חשד להפרת זכויות עבודה, מומלץ:
1. לפנות למעסיק בכתב לבירור הנושא
2. לשמור את כל תלושי השכר והמסמכים הרלוונטיים
3. להתייעץ עם עורך דין המתמחה בדיני עבודה
4. לשקול פנייה למשרד העבודה או לבית הדין לעבודה

מקורות מידע נוספים:
- משרד העבודה והרווחה: www.gov.il/he/departments/ministry_of_labor
- קו החם לזכויות עובדים: *6050
"""

# Report footer
REPORT_FOOTER = """
---
דוח זה נוצר אוטומטית על ידי מערכת SalaryValidator
תאריך הפקה: {date}
"""


def get_violation_type_name(violation_type: ViolationType) -> str:
    """Get Hebrew name for violation type."""
    return VIOLATION_TYPE_NAMES_HE.get(violation_type, str(violation_type.value))


def get_hebrew_month(month: int) -> str:
    """Get Hebrew month name."""
    return HEBREW_MONTHS.get(month, str(month))


def get_risk_level_text(risk_level: str) -> tuple[str, str]:
    """Get Hebrew risk level name and description."""
    name = RISK_LEVEL_HE.get(risk_level, risk_level)
    desc = RISK_LEVEL_DESCRIPTIONS.get(risk_level, "")
    return name, desc


def get_recommendation(violation_type: ViolationType) -> str:
    """Get recommendation for a violation type."""
    return RECOMMENDATIONS.get(violation_type, "יש לבדוק את הנושא עם מומחה.")
