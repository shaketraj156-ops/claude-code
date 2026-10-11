"""Short brief for the BMC officer, in English or Hindi.

Every number comes from code. Claude (optional) only rewords the text.
If the API is missing or fails, the plain template is returned.
"""
import os


def _evidence_text(e):
    unit = f" {e['unit']}" if e["unit"] else ""
    return (f"{e['parameter']} {e['value']:g}{unit} (limit: {e['limit']}), "
            f"{e['year']} {e['festival']} {e['phase']}, report page {e['source_page']}")


def _gaps_text(ranked, lang):
    lines = []
    for _, r in ranked.iterrows():
        for year, fest in r["table_gaps"]:
            if lang == "hi":
                lines.append(f"{r['site']}: {year} {fest} ka table report mein nahi hai")
            else:
                lines.append(f"{r['site']}: no {year} {fest} table in the report")
        if r["n_missing"]:
            if lang == "hi":
                lines.append(f"{r['site']}: {r['n_missing']} readings sample nahi hui (missing)")
            else:
                lines.append(f"{r['site']}: {r['n_missing']} readings not sampled (missing)")
    return lines


def plain_brief(ranked, lang="en", top_n=3):
    top = ranked.head(top_n)
    gaps = _gaps_text(ranked, lang)
    body = []
    for i, r in top.iterrows():
        score = "no data" if r["risk_score"] is None else f"{r['risk_score']}/100"
        body.append(f"{i + 1}. {r['site']} - risk score {score}")
        for e in r["evidence"]:
            body.append(f"   - {_evidence_text(e)}")
    gap_block = "\n".join(f"- {g}" for g in gaps) or "- none"

    if lang == "hi":
        return (
            "विसर्जन घाट जोखिम सार (CPCB वर्ग B, बाहरी स्नान मानक)\n\n"
            "सबसे ज़्यादा ध्यान देने योग्य घाट:\n" + "\n".join(body) + "\n\n"
            "डेटा की कमी (missing का मतलब साफ़ पानी नहीं है):\n" + gap_block + "\n\n"
            "नोट: यह केवल रीडिंग की सीमा से तुलना है। स्वास्थ्य पर असर का कोई दावा नहीं है। "
            "स्रोत: MPPCB विसर्जन रिपोर्ट 2023-2025। इकाइयाँ मानक मानी गई हैं, रिपोर्ट में छपी नहीं हैं।"
        )
    return (
        "Visarjan ghat risk brief (CPCB Class B, outdoor bathing standard)\n\n"
        "Ghats needing most attention:\n" + "\n".join(body) + "\n\n"
        "Data gaps (missing does not mean clean):\n" + gap_block + "\n\n"
        "Note: readings are compared with limits only. No health effect is claimed. "
        "Source: MPPCB visarjan reports 2023-2025. Units are assumed standard; "
        "the reports do not print them."
    )


def claude_brief(text, lang):
    """Optional: let Claude reword the plain brief. Numbers must not change."""
    import anthropic
    client = anthropic.Anthropic()          # reads ANTHROPIC_API_KEY
    language = "Hindi (Devanagari)" if lang == "hi" else "English"
    msg = client.messages.create(
        model="claude-sonnet-5-5",
        max_tokens=900,
        messages=[{"role": "user", "content": (
            f"Rewrite this brief in simple {language} for a municipal officer. "
            "Keep every number, ghat name and page number exactly as given. "
            "Do not add any fact, number or health claim.\n\n" + text)}],
    )
    return msg.content[0].text


def make_brief(ranked, lang="en", use_claude=False):
    text = plain_brief(ranked, lang)
    if use_claude and os.environ.get("ANTHROPIC_API_KEY"):
        try:
            return claude_brief(text, lang)
        except Exception:
            pass                             # fall back to the plain brief
    return text
