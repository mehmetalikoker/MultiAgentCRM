class AgentState(TypedDict):
    campaign_text: str
    image_path: str
    compliance_report: str       # 1. Aşama sonucu
    visual_report: str           # 2. Aşama sonucu
    legal_audit_report: str      # 3. Aşama sonucu (BDDK vb.)
    final_score: int             # 0-100 arası uygunluk puanı