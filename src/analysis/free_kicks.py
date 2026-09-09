from collections import Counter

import pandas as pd
import plotly.express as px
import streamlit as st

from src.reports.report_items import (
    create_image_report_item,
    create_kpi_report_item,
    create_plotly_report_item,
    create_table_report_item,
)

from src.reports.report_ui import (
    render_add_to_report_button,
    render_create_report_button,
)

FC_WON = "1ST CONTACT WON"
FC_LOST = "1ST CONTACT LOST"
SHOT = "SHOT"
GOAL = "GOAL"
SHOT_CONCEDED = "SHOT CONCEDED"
GOAL_CONCEDED = "GOAL CONCEDED"
SECOND_PHASE_ATTACK = "2ND PHASE ATTACK"
SECOND_PHASE = "2ND PHASE"
COUNTER_ALLOWED = "COUNTER ALLOWED"
COUNTER_LAUNCHED = "COUNTER LAUNCHED"
CLEARANCE = "CLEARANCE"


# ============================================================
# FREE-KICK ZONE VISUALISATION
# ============================================================

ORIGIN_ZONE_ALIAS_TO_SLOT = {
    "Z1 LEFT": "z1_left",
    "Z1 RIGHT": "z1_right",
    "Z2 LEFT": "z2_left",
    "Z2 RIGHT": "z2_right",
    "CENTRAL": "central",
    "DEEP ZONES": "deep_zones",
    "DEEP ZONE": "deep_zones",
}

ORIGIN_ZONE_DISPLAY_NAMES = {
    "z1_left": "Z1 LEFT",
    "z1_right": "Z1 RIGHT",
    "z2_left": "Z2 LEFT",
    "z2_right": "Z2 RIGHT",
    "central": "CENTRAL",
    "deep_zones": "DEEP ZONES",
}

NUMBERED_ZONE_ALIAS_TO_SLOT = {
    "Z1": "z1",
    "Z 1": "z1",
    "Z2": "z2",
    "Z 2": "z2",
    "Z3": "z3",
    "Z 3": "z3",
    "Z4": "z4",
    "Z 4": "z4",
    "Z5": "z5",
    "Z 5": "z5",
    "Z6": "z6",
    "Z 6": "z6",
    "Z7": "z7",
    "Z 7": "z7",
    "Z8": "z8",
    "Z 8": "z8",
    "Z9": "z9",
    "Z 9": "z9",
    "Z10": "z10",
    "Z 10": "z10",
    "Z11": "z11",
    "Z 11": "z11",
    "Z12": "z12",
    "Z 12": "z12",
}

NUMBERED_ZONE_DISPLAY_NAMES = {
    "z1": "Z1",
    "z2": "Z2",
    "z3": "Z3",
    "z4": "Z4",
    "z5": "Z5",
    "z6": "Z6",
    "z7": "Z7",
    "z8": "Z8",
    "z9": "Z9",
    "z10": "Z10",
    "z11": "Z11",
    "z12": "Z12",
}


def _as_list(value):
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _normalize(value):
    if value is None:
        return ""
    return " ".join(str(value).strip().upper().split())


def event_has_value(record, key, target):
    target = _normalize(target)
    return any(_normalize(v) == target for v in _as_list(record.get(key)))


def event_has_any_value(record, key, targets):
    return any(event_has_value(record, key, target) for target in targets)


def count_events_with_value(records, key, target):
    return sum(1 for r in records if event_has_value(r, key, target))


def count_events_with_any_value(records, key, targets):
    return sum(1 for r in records if event_has_any_value(r, key, targets))


def calculate_rate(numerator, denominator):
    return 0.0 if denominator == 0 else numerator / denominator * 100


def format_rate(numerator, denominator):
    if denominator == 0:
        return "—"
    return f"{calculate_rate(numerator, denominator):.0f}% ({numerator}/{denominator})"


def get_record_values(record, key, include_unknown=False):
    values, seen = [], set()
    for raw in _as_list(record.get(key)):
        if raw is None:
            continue
        value = str(raw).strip()
        if not value:
            continue
        normalized = _normalize(value)
        if normalized in seen:
            continue
        seen.add(normalized)
        values.append(value)
    if not values and include_unknown:
        return ["UNKNOWN"]
    return values


def category_counts(records, key, include_unknown=False):
    counts = Counter()
    for record in records:
        for value in get_record_values(record, key, include_unknown):
            counts[value] += 1
    return counts


def records_with_category(records, key, category):
    if category == "UNKNOWN":
        return [r for r in records if not get_record_values(r, key)]
    return [r for r in records if event_has_value(r, key, category)]


def most_common(records, key, include_unknown=False):
    counts = category_counts(records, key, include_unknown)
    return counts.most_common(1)[0] if counts else ("-", 0)


def resolve_phase(analysis, phase):
    if phase:
        return str(phase).lower()
    if analysis.get("phase"):
        return str(analysis["phase"]).lower()
    return "offensive"


def get_free_kick_metrics(records, phase):
    total = len(records)
    fc_won = count_events_with_value(records, "first_contact", FC_WON)
    clearance = count_events_with_value(records, "outcome", CLEARANCE)

    if phase == "defensive":
        attempt = count_events_with_any_value(
            records,
            "outcome",
            [SHOT_CONCEDED, GOAL_CONCEDED],
        )
        goal = count_events_with_value(records, "outcome", GOAL_CONCEDED)
        second_phase = count_events_with_value(records, "outcome", SECOND_PHASE)
        counter = count_events_with_value(records, "outcome", COUNTER_LAUNCHED)
    else:
        # GOAL may be a terminal outcome without SHOT.
        # Therefore Attempt = SHOT OR GOAL.
        attempt = count_events_with_any_value(records, "outcome", [SHOT, GOAL])
        goal = count_events_with_value(records, "outcome", GOAL)
        second_phase = count_events_with_value(records, "outcome", SECOND_PHASE_ATTACK)
        counter = count_events_with_value(records, "outcome", COUNTER_ALLOWED)

    return {
        "total": total,
        "fc_won": fc_won,
        "attempt": attempt,
        "goal": goal,
        "second_phase": second_phase,
        "counter": counter,
        "clearance": clearance,
    }


def render_kpis(
    records,
    phase,
    report_context: dict | None = None,
):
    m = get_free_kick_metrics(records, phase)
    total = m["total"]
    delivery_type, delivery_count = most_common(records, "delivery_type")

    st.markdown("### Key KPIs")

    if phase == "defensive":
        opp, opp_count = most_common(records, "opponent_players", include_unknown=True)
        rows = [
            [
                ("Free Kicks Faced", str(total), None),
                ("First Contact Won", format_rate(m["fc_won"], total), None),
                ("Attempt Conceded", format_rate(m["attempt"], total), "SHOT CONCEDED or GOAL CONCEDED."),
                ("Goal Conceded", format_rate(m["goal"], total), None),
            ],
            [
                ("Goal Conceded Conversion", format_rate(m["goal"], m["attempt"]), "GOAL CONCEDED / Attempt Conceded."),
                ("2nd Phase", format_rate(m["second_phase"], total), None),
                ("Counter Launched", format_rate(m["counter"], total), None),
                ("Most Common Delivery Type", delivery_type, f"{delivery_count}/{total} free kicks"),
            ],
            [
                ("Most Common Opponent Players", opp, f"{opp_count}/{total} free kicks"),
            ],
        ]
    else:
        taker, taker_count = most_common(records, "taker", include_unknown=True)
        rows = [
            [
                ("Total Free Kicks", str(total), None),
                ("First Contact Won", format_rate(m["fc_won"], total), None),
                ("Attempt", format_rate(m["attempt"], total), "Attempt = SHOT or GOAL."),
                ("Goal", format_rate(m["goal"], total), None),
            ],
            [
                ("Goal Conversion", format_rate(m["goal"], m["attempt"]), "GOAL / Attempt."),
                ("2nd Phase Attack", format_rate(m["second_phase"], total), None),
                ("Counter Allowed", format_rate(m["counter"], total), None),
                ("Most Common Delivery Type", delivery_type, f"{delivery_count}/{total} free kicks"),
            ],
            [
                ("Most Common Taker", taker, f"{taker_count}/{total} free kicks"),
            ],
        ]

    for row in rows:
        cols = st.columns(len(row))
        for col, (label, value, help_text) in zip(cols, row):
            with col:
                st.metric(label, value, help=help_text)

    if report_context is not None:
        kpi_items = []

        for row in rows:
            for (
                label,
                value,
                _help_text,
            ) in row:
                kpi_items.append(
                    {
                        "label": label,
                        "value": value,
                    }
                )

        report_item = create_kpi_report_item(
            module="free_kick",
            section_title="Key KPIs",
            kpis=kpi_items,
            context=report_context,
        )

        render_add_to_report_button(
            report_item,
            key=(
                "report_free_kick_kpis_"
                f"{report_item['id']}"
            ),
        )



def build_visual_zone_counts(records, key, alias_map, slots):
    counts = {
        slot: 0
        for slot in slots
    }

    for record in records:
        seen_slots = set()

        for value in get_record_values(
            record,
            key,
        ):
            slot = alias_map.get(
                _normalize(value)
            )

            if (
                slot
                and slot not in seen_slots
            ):
                counts[slot] += 1
                seen_slots.add(slot)

    return counts


def _free_kick_zone_bg(
    count,
    max_count,
    palette,
):
    ratio = (
        0
        if max_count <= 0
        else count / max_count
    )

    if palette == "finishing":
        if count == 0:
            return "rgba(90, 13, 40, 0.28)"
        if ratio >= 0.75:
            return "rgba(170, 18, 65, 0.78)"
        if ratio >= 0.50:
            return "rgba(145, 15, 55, 0.66)"
        return "rgba(120, 12, 48, 0.52)"

    if count == 0:
        return "rgba(0, 70, 78, 0.27)"
    if ratio >= 0.75:
        return "rgba(0, 112, 124, 0.74)"
    if ratio >= 0.50:
        return "rgba(0, 95, 107, 0.62)"
    return "rgba(0, 80, 92, 0.48)"


def _free_kick_zone_card(
    slot,
    label,
    count,
    max_count,
    palette,
):
    bg = _free_kick_zone_bg(
        count,
        max_count,
        palette,
    )

    return f"""
    <div
        class="fk-zone-card {slot}"
        style="background:{bg};"
    >
        <div class="fk-zone-name">
            {label}
        </div>

        <div class="fk-zone-count">
            {count}
        </div>
    </div>
    """


def _origin_zone_panel(
    counts,
):
    max_count = max(
        counts.values(),
        default=0,
    )

    return f"""
    <div class="fk-pitch-panel">

        <div class="fk-pitch-title">
            ORIGIN ZONES
        </div>

        <div class="fk-pitch origin-pitch">

            <div class="fk-pitch-lines">
                <div class="fk-penalty-box"></div>
                <div class="fk-goal-box"></div>
                <div class="fk-penalty-arc"></div>
                <div class="fk-halfway"></div>
                <div class="fk-centre-circle"></div>
                <div class="fk-centre-dot"></div>
            </div>

            {_free_kick_zone_card(
                "origin-z1-left",
                ORIGIN_ZONE_DISPLAY_NAMES["z1_left"],
                counts["z1_left"],
                max_count,
                "delivery",
            )}

            {_free_kick_zone_card(
                "origin-z1-right",
                ORIGIN_ZONE_DISPLAY_NAMES["z1_right"],
                counts["z1_right"],
                max_count,
                "delivery",
            )}

            {_free_kick_zone_card(
                "origin-z2-left",
                ORIGIN_ZONE_DISPLAY_NAMES["z2_left"],
                counts["z2_left"],
                max_count,
                "delivery",
            )}

            {_free_kick_zone_card(
                "origin-z2-right",
                ORIGIN_ZONE_DISPLAY_NAMES["z2_right"],
                counts["z2_right"],
                max_count,
                "delivery",
            )}

            {_free_kick_zone_card(
                "origin-central",
                ORIGIN_ZONE_DISPLAY_NAMES["central"],
                counts["central"],
                max_count,
                "delivery",
            )}

            {_free_kick_zone_card(
                "origin-deep",
                ORIGIN_ZONE_DISPLAY_NAMES["deep_zones"],
                counts["deep_zones"],
                max_count,
                "delivery",
            )}

        </div>

    </div>
    """


def _numbered_zone_panel(
    title,
    counts,
    palette,
):
    max_count = max(
        counts.values(),
        default=0,
    )

    return f"""
    <div class="fk-pitch-panel">

        <div class="fk-pitch-title">
            {title}
        </div>

        <div class="fk-pitch numbered-pitch">

            <div class="fk-pitch-lines">
                <div class="fk-penalty-box"></div>
                <div class="fk-goal-box"></div>
                <div class="fk-penalty-arc"></div>
                <div class="fk-halfway"></div>
                <div class="fk-centre-circle"></div>
                <div class="fk-centre-dot"></div>
            </div>

            {_free_kick_zone_card(
                "z8",
                "Z8",
                counts["z8"],
                max_count,
                palette,
            )}

            {_free_kick_zone_card(
                "z10",
                "Z10",
                counts["z10"],
                max_count,
                palette,
            )}

            {_free_kick_zone_card(
                "z4",
                "Z4",
                counts["z4"],
                max_count,
                palette,
            )}

            {_free_kick_zone_card(
                "z6",
                "Z6",
                counts["z6"],
                max_count,
                palette,
            )}

            {_free_kick_zone_card(
                "z1",
                "Z1",
                counts["z1"],
                max_count,
                palette,
            )}

            {_free_kick_zone_card(
                "z2",
                "Z2",
                counts["z2"],
                max_count,
                palette,
            )}

            {_free_kick_zone_card(
                "z3",
                "Z3",
                counts["z3"],
                max_count,
                palette,
            )}

            {_free_kick_zone_card(
                "z5",
                "Z5",
                counts["z5"],
                max_count,
                palette,
            )}

            {_free_kick_zone_card(
                "z7",
                "Z7",
                counts["z7"],
                max_count,
                palette,
            )}

            {_free_kick_zone_card(
                "z9",
                "Z9",
                counts["z9"],
                max_count,
                palette,
            )}

            {_free_kick_zone_card(
                "z11",
                "Z11",
                counts["z11"],
                max_count,
                palette,
            )}

            {_free_kick_zone_card(
                "z12",
                "Z12",
                counts["z12"],
                max_count,
                palette,
            )}

        </div>

    </div>
    """


def render_zone_visualisation(
    records,
    report_context: dict | None = None,
):
    st.markdown(
        "### Zone Visualisation"
    )

    origin_counts = (
        build_visual_zone_counts(
            records,
            "origin_zone",
            ORIGIN_ZONE_ALIAS_TO_SLOT,
            ORIGIN_ZONE_DISPLAY_NAMES,
        )
    )

    delivery_counts = (
        build_visual_zone_counts(
            records,
            "delivery_zone",
            NUMBERED_ZONE_ALIAS_TO_SLOT,
            NUMBERED_ZONE_DISPLAY_NAMES,
        )
    )

    finishing_counts = (
        build_visual_zone_counts(
            records,
            "finishing_zone",
            NUMBERED_ZONE_ALIAS_TO_SLOT,
            NUMBERED_ZONE_DISPLAY_NAMES,
        )
    )

    total = len(records)

    origin_mapped = sum(
        origin_counts.values()
    )

    delivery_mapped = sum(
        delivery_counts.values()
    )

    finishing_mapped = sum(
        finishing_counts.values()
    )

    html = f"""
<!doctype html>
<html>
<head>
<meta charset="UTF-8">

<style>

* {{
    box-sizing: border-box;
}}

html,
body {{
    margin: 0;
    padding: 0;
    background: #0d1117;
    color: #ffffff;
    font-family:
        -apple-system,
        BlinkMacSystemFont,
        "Segoe UI",
        sans-serif;
}}

.fk-zone-shell {{
    width: 100%;
}}

.fk-zone-grid {{
    display: grid;
    grid-template-columns:
        1fr 1fr 1fr;
    gap: 10px;
}}

.fk-pitch-panel {{
    min-width: 0;
}}

.fk-pitch-title {{
    height: 28px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #c7f000;
    font-size: 12px;
    font-weight: 800;
    letter-spacing: .25px;
}}

.fk-pitch {{
    position: relative;
    height: 330px;
    overflow: hidden;
    border:
        2px solid
        rgba(255,255,255,.90);

    background:
        repeating-linear-gradient(
            75deg,
            rgba(255,255,255,.035) 0px,
            rgba(255,255,255,.035) 5px,
            transparent 5px,
            transparent 24px
        ),
        linear-gradient(
            180deg,
            #14202a 0%,
            #101922 60%,
            #0d151c 60%,
            #0b1218 100%
        );
}}

.fk-pitch-lines {{
    position: absolute;
    inset: 0;
    z-index: 10;
    pointer-events: none;
}}

.fk-penalty-box {{
    position: absolute;
    top: 0;
    left: 20%;
    width: 60%;
    height: 28%;
    border-left:
        2px solid
        rgba(255,255,255,.92);
    border-right:
        2px solid
        rgba(255,255,255,.92);
    border-bottom:
        2px solid
        rgba(255,255,255,.92);
}}

.fk-goal-box {{
    position: absolute;
    top: 0;
    left: 38%;
    width: 24%;
    height: 12%;
    border-left:
        2px solid
        rgba(255,255,255,.88);
    border-right:
        2px solid
        rgba(255,255,255,.88);
    border-bottom:
        2px solid
        rgba(255,255,255,.88);
}}

.fk-penalty-arc {{
    position: absolute;
    top: 27%;
    left: 39%;
    width: 22%;
    height: 13%;
    border-bottom:
        2px solid
        rgba(255,255,255,.90);
    border-radius:
        0 0 100px 100px;
}}

.fk-halfway {{
    position: absolute;
    left: 0;
    right: 0;
    top: 72%;
    border-top:
        2px solid
        rgba(255,255,255,.92);
}}

.fk-centre-circle {{
    position: absolute;
    left: 38.5%;
    top: calc(72% - 42px);
    width: 23%;
    height: 84px;
    border:
        2px solid
        rgba(255,255,255,.92);
    border-radius: 50%;
}}

.fk-centre-dot {{
    position: absolute;
    width: 5px;
    height: 5px;
    left: calc(50% - 2.5px);
    top: calc(72% - 2.5px);
    background:
        rgba(255,255,255,.95);
    border-radius: 50%;
}}

.fk-zone-card {{
    position: absolute;
    z-index: 2;

    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;

    text-align: center;

    border:
        1px solid
        rgba(255,255,255,.11);

    padding:
        3px;

    overflow:
        hidden;
}}

.fk-zone-name {{
    width: 100%;
    font-size: 9px;
    font-weight: 700;
    line-height: 1.05;
    color:
        rgba(255,255,255,.66);
}}

.fk-zone-count {{
    margin-top: 3px;
    font-size: 15px;
    line-height: 1;
    font-weight: 800;
    color: #ffffff;
}}

/* ============================================================
   ORIGIN ZONES
   ============================================================ */

.origin-z1-left {{
    left: 0;
    top: 0;
    width: 20%;
    height: 28%;
}}

.origin-z1-right {{
    right: 0;
    top: 0;
    width: 20%;
    height: 28%;
}}

.origin-z2-left {{
    left: 0;
    top: 28%;
    width: 20%;
    height: 32%;
}}

.origin-z2-right {{
    right: 0;
    top: 28%;
    width: 20%;
    height: 32%;
}}

.origin-central {{
    left: 20%;
    top: 0;
    width: 60%;
    height: 60%;
    background:
        rgba(0, 86, 96, 0.42) !important;
}}

.origin-deep {{
    left: 0;
    top: 60%;
    width: 100%;
    height: 40%;
    background:
        rgba(0, 92, 102, 0.50) !important;
}}

/* ============================================================
   DELIVERY / FINISHING ZONES
   ============================================================ */

.z8 {{
    left: 0;
    top: 0;
    width: 20%;
    height: 34%;
}}

.z10 {{
    left: 0;
    top: 34%;
    width: 20%;
    height: 25%;
}}

.z9 {{
    right: 0;
    top: 0;
    width: 20%;
    height: 34%;
}}

.z11 {{
    right: 0;
    top: 34%;
    width: 20%;
    height: 25%;
}}

.z4 {{
    left: 20%;
    top: 0;
    width: 16%;
    height: 16%;
}}

.z6 {{
    left: 20%;
    top: 16%;
    width: 16%;
    height: 12%;
}}

.z1 {{
    left: 36%;
    top: 0;
    width: 28%;
    height: 8%;
    background:
        rgba(215,215,215,.82) !important;
    color: #111111;
}}

.z2 {{
    left: 36%;
    top: 8%;
    width: 28%;
    height: 8%;
    background:
        rgba(130,130,130,.68) !important;
}}

.z3 {{
    left: 36%;
    top: 16%;
    width: 28%;
    height: 12%;
}}

.z5 {{
    left: 64%;
    top: 0;
    width: 16%;
    height: 16%;
}}

.z7 {{
    left: 64%;
    top: 16%;
    width: 16%;
    height: 12%;
}}

.z12 {{
    left: 20%;
    top: 28%;
    width: 60%;
    height: 12%;
    background:
        rgba(0, 83, 94, 0.42);
}}

.fk-zone-caption {{
    margin-top: 8px;
    display: grid;
    grid-template-columns:
        1fr 1fr 1fr;
    gap: 10px;
    font-size: 10px;
    color:
        rgba(255,255,255,.55);
}}

.fk-zone-caption > div {{
    text-align: center;
}}

@media (
    max-width: 1000px
) {{
    .fk-zone-grid,
    .fk-zone-caption {{
        grid-template-columns:
            1fr;
    }}
}}

</style>
</head>

<body>

<div class="fk-zone-shell">

    <div class="fk-zone-grid">

        {_origin_zone_panel(
            origin_counts,
        )}

        {_numbered_zone_panel(
            "DELIVERY ZONES",
            delivery_counts,
            "delivery",
        )}

        {_numbered_zone_panel(
            "FINISHING ZONES",
            finishing_counts,
            "finishing",
        )}

    </div>

    <div class="fk-zone-caption">

        <div>
            Origin-zone labels available:
            <strong>
                {origin_mapped}/{total}
            </strong>
        </div>

        <div>
            Delivery-zone labels available:
            <strong>
                {delivery_mapped}/{total}
            </strong>
        </div>

        <div>
            Finishing-zone labels available:
            <strong>
                {finishing_mapped}/{total}
            </strong>
        </div>

    </div>

</div>

</body>
</html>
"""

    st.iframe(
        html,
        width="stretch",
        height=395,
    )

    if report_context is not None:
        report_item = create_image_report_item(
            module="free_kick",
            section_title="Zone Visualisation",
            html=html,
            context=report_context,
            width_px=1400,
            height_px=395,
        )

        render_add_to_report_button(
            report_item,
            key=(
                "report_free_kick_zone_visualisation_"
                f"{report_item['id']}"
            ),
        )


def build_outcome_dataframe(records):
    total = len(records)
    rows = []
    for outcome, count in category_counts(records, "outcome").items():
        rows.append({
            "Outcome": outcome,
            "Count": count,
            "Percentage": calculate_rate(count, total),
            "Display": format_rate(count, total),
        })
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    return df.sort_values("Percentage", ascending=True).reset_index(drop=True)


def render_outcome_breakdown(
    records,
    report_context: dict | None = None,
):
    st.markdown("### Outcome Breakdown")
    df = build_outcome_dataframe(records)
    if df.empty:
        st.info("No OUTCOME data available.")
        return

    total = len(records)
    fig = px.bar(
        df,
        x="Percentage",
        y="Outcome",
        orientation="h",
        text="Display",
        custom_data=["Count"],
    )
    fig.update_traces(
        textposition="outside",
        cliponaxis=False,
        hovertemplate=(
            "<b>%{y}</b><br>%{x:.0f}% "
            f"(%{{customdata[0]}}/{total})<extra></extra>"
        ),
    )
    fig.update_layout(
        height=max(280, 52 * len(df)),
        margin=dict(l=20, r=130, t=10, b=20),
        xaxis_title="Free Kick Rate (%)",
        yaxis_title="",
        xaxis=dict(range=[0, 110]),
        showlegend=False,
    )
    st.plotly_chart(fig, width="stretch")
    st.caption(
        "Attempt = SHOT OR GOAL for offensive free kicks. "
        "Attempt Conceded = SHOT CONCEDED OR GOAL CONCEDED for defensive free kicks."
    )

    if report_context is not None:
        report_item = create_plotly_report_item(
            module="free_kick",
            section_title="Outcome Breakdown",
            figure=fig,
            context=report_context,
        )

        render_add_to_report_button(
            report_item,
            key=(
                "report_free_kick_outcome_"
                f"{report_item['id']}"
            ),
        )


def build_effectiveness_dataframe(records, group_key, phase, include_unknown=False, first_contact_table=False):
    rows = []
    for category in category_counts(records, group_key, include_unknown):
        category_records = records_with_category(records, group_key, category)
        m = get_free_kick_metrics(category_records, phase)
        total = m["total"]

        row = {
            "Category": category,
            "Free Kicks": total,
            "FC Won %": calculate_rate(m["fc_won"], total),
            "Attempt %": calculate_rate(m["attempt"], total),
            "Goal %": calculate_rate(m["goal"], total),
        }

        if not first_contact_table:
            row["FC Won"] = format_rate(m["fc_won"], total)

        if phase == "defensive":
            row.update({
                "Attempt Conceded": format_rate(m["attempt"], total),
                "Goal Conceded": format_rate(m["goal"], total),
                "Goal Conversion": format_rate(m["goal"], m["attempt"]),
            })
        else:
            row.update({
                "Attempt": format_rate(m["attempt"], total),
                "Goal": format_rate(m["goal"], total),
                "Goal Conversion": format_rate(m["goal"], m["attempt"]),
            })

        rows.append(row)

    df = pd.DataFrame(rows)
    if df.empty:
        return df
    return df.sort_values("Free Kicks", ascending=False).reset_index(drop=True)


def render_first_contact_chart(
    records,
    phase,
    report_context: dict | None = None,
):
    rows = []
    for category in [FC_LOST, FC_WON]:
        category_records = records_with_category(records, "first_contact", category)
        if not category_records:
            continue

        m = get_free_kick_metrics(category_records, phase)
        total = m["total"]

        metrics = (
            [("Attempt Conceded", m["attempt"]), ("Goal Conceded", m["goal"])]
            if phase == "defensive"
            else [("Attempt", m["attempt"]), ("Goal", m["goal"])]
        )

        for metric, count in metrics:
            rows.append({
                "First Contact": category,
                "Metric": metric,
                "Rate": calculate_rate(count, total),
                "Count": count,
                "Total": total,
                "Display": format_rate(count, total),
            })

    df = pd.DataFrame(rows)
    if df.empty:
        return

    fig = px.bar(
        df,
        x="First Contact",
        y="Rate",
        color="Metric",
        barmode="group",
        text="Display",
        custom_data=["Count", "Total"],
    )
    fig.update_traces(
        textposition="outside",
        cliponaxis=False,
        hovertemplate=(
            "<b>%{x}</b><br>%{fullData.name}: %{y:.0f}% "
            "(%{customdata[0]}/%{customdata[1]})<extra></extra>"
        ),
    )
    fig.update_layout(
        height=350,
        margin=dict(l=20, r=20, t=10, b=20),
        xaxis_title="",
        yaxis_title="Rate (%)",
        yaxis=dict(range=[0, 118]),
        legend_title="",
    )
    st.plotly_chart(fig, width="stretch")

    if report_context is not None:
        report_item = create_plotly_report_item(
            module="free_kick",
            section_title="First Contact → Outcome",
            figure=fig,
            context=report_context,
        )

        render_add_to_report_button(
            report_item,
            key=(
                "report_free_kick_first_contact_"
                f"{report_item['id']}"
            ),
        )


def render_delivery_type_scatter(
    records,
    phase,
    report_context: dict | None = None,
):
    rows = []

    for category in category_counts(
        records,
        "delivery_type",
    ):
        category_records = (
            records_with_category(
                records,
                "delivery_type",
                category,
            )
        )

        m = get_free_kick_metrics(
            category_records,
            phase,
        )

        total = m["total"]

        if total == 0:
            continue

        rows.append(
            {
                "Delivery Type":
                    category,

                "Free Kicks":
                    total,

                "FC Won Rate":
                    calculate_rate(
                        m["fc_won"],
                        total,
                    ),

                "Attempt Rate":
                    calculate_rate(
                        m["attempt"],
                        total,
                    ),

                "FC Won Display":
                    format_rate(
                        m["fc_won"],
                        total,
                    ),

                "Attempt Display":
                    format_rate(
                        m["attempt"],
                        total,
                    ),

                "Goal Display":
                    format_rate(
                        m["goal"],
                        total,
                    ),

                "Goal Conversion":
                    format_rate(
                        m["goal"],
                        m["attempt"],
                    ),
            }
        )

    df = pd.DataFrame(
        rows
    )

    if df.empty:
        st.info(
            "No delivery-type data available."
        )
        return

    if phase == "defensive":
        attempt_label = (
            "Attempt Conceded"
        )

        goal_label = (
            "Goal Conceded"
        )

        y_title = (
            "Attempt Conceded Rate (%)"
        )

    else:
        attempt_label = "Attempt"
        goal_label = "Goal"
        y_title = "Attempt Rate (%)"

    x_min = max(
        0.0,
        float(
            df["FC Won Rate"].min()
        ) - 8.0,
    )

    x_max = min(
        100.0,
        float(
            df["FC Won Rate"].max()
        ) + 8.0,
    )

    if (
        x_max - x_min
    ) < 28:
        x_center = (
            x_min + x_max
        ) / 2

        x_min = max(
            0.0,
            x_center - 14,
        )

        x_max = min(
            100.0,
            x_center + 14,
        )

    text_positions = [
        (
            "bottom center"
            if attempt_rate >= 94
            else "top center"
        )
        for attempt_rate
        in df["Attempt Rate"]
    ]

    fig = px.scatter(
        df,
        x="FC Won Rate",
        y="Attempt Rate",
        text="Delivery Type",
        custom_data=[
            "Free Kicks",
            "FC Won Display",
            "Attempt Display",
            "Goal Display",
            "Goal Conversion",
        ],
    )

    fig.update_traces(
        mode="markers+text",
        textposition=text_positions,
        textfont=dict(
            size=10,
        ),
        cliponaxis=False,
        marker=dict(
            size=7,
            opacity=0.92,
            line=dict(
                width=1,
                color=(
                    "rgba(255,255,255,0.55)"
                ),
            ),
        ),
        hovertemplate=(
            "<b>%{text}</b><br>"
            "Free Kicks: "
            "%{customdata[0]}<br>"
            "FC Won: "
            "%{customdata[1]}<br>"
            f"{attempt_label}: "
            "%{customdata[2]}<br>"
            f"{goal_label}: "
            "%{customdata[3]}<br>"
            "Goal Conversion: "
            "%{customdata[4]}"
            "<extra></extra>"
        ),
    )

    fig.add_vline(
        x=50,
        line_width=1,
        line_dash="dot",
        opacity=0.20,
    )

    fig.add_hline(
        y=50,
        line_width=1,
        line_dash="dot",
        opacity=0.20,
    )

    fig.update_layout(
        height=205,
        margin=dict(
            l=20,
            r=15,
            t=12,
            b=15,
        ),
        xaxis_title=(
            "First Contact Won (%)"
        ),
        yaxis_title=y_title,
        xaxis=dict(
            range=[
                x_min,
                x_max,
            ],
            dtick=10,
            zeroline=False,
            fixedrange=True,
        ),
        yaxis=dict(
            range=[
                -4,
                108,
            ],
            dtick=25,
            zeroline=False,
            fixedrange=True,
        ),
        showlegend=False,
    )

    chart_col, spacer_col = st.columns(
        [
            1.25,
            1.0,
        ]
    )

    with chart_col:
        st.plotly_chart(
            fig,
            width="stretch",
            config={
                "displayModeBar":
                    False,
                "displaylogo":
                    False,
                "scrollZoom":
                    False,
            },
        )

    if report_context is not None:
        report_item = create_plotly_report_item(
            module="free_kick",
            section_title=(
                "Delivery Type Effectiveness — Scatter"
            ),
            figure=fig,
            context=report_context,
        )

        render_add_to_report_button(
            report_item,
            key=(
                "report_free_kick_delivery_scatter_"
                f"{report_item['id']}"
            ),
        )


def render_effectiveness_table(
    title,
    records,
    group_key,
    phase,
    category_name,
    include_unknown=False,
    first_contact_table=False,
    show_title=True,
    report_context: dict | None = None,
    report_section_title: str | None = None,
):
    if show_title:
        st.markdown(f"#### {title}")

    df = build_effectiveness_dataframe(
        records,
        group_key,
        phase,
        include_unknown,
        first_contact_table,
    )
    if df.empty:
        st.info("No data available.")
        return

    df = df.rename(columns={"Category": category_name})

    if phase == "defensive":
        display_columns = (
            [category_name, "Free Kicks", "Attempt Conceded", "Goal Conceded", "Goal Conversion"]
            if first_contact_table
            else [category_name, "Free Kicks", "FC Won", "Attempt Conceded", "Goal Conceded", "Goal Conversion"]
        )
    else:
        display_columns = (
            [category_name, "Free Kicks", "Attempt", "Goal", "Goal Conversion"]
            if first_contact_table
            else [category_name, "Free Kicks", "FC Won", "Attempt", "Goal", "Goal Conversion"]
        )

    display_df = df[display_columns].copy().rename(
        columns={"Free Kicks": "FKs", "Goal Conversion": "Goal Conv."}
    )

    st.dataframe(
        display_df,
        hide_index=True,
        width="stretch",
        column_config={
            category_name: st.column_config.TextColumn(category_name, width="large"),
            "FKs": st.column_config.NumberColumn("FKs", width="small"),
        },
    )

    if report_context is not None:
        section_title = (
            report_section_title
            or title
            or f"{category_name} Effectiveness"
        )

        report_item = create_table_report_item(
            module="free_kick",
            section_title=section_title,
            dataframe=display_df,
            context=report_context,
        )

        render_add_to_report_button(
            report_item,
            key=(
                "report_free_kick_effectiveness_table_"
                f"{group_key}_"
                f"{report_item['id']}"
            ),
        )


def render_effectiveness(
    records,
    phase,
    analysis_scope: str | None = None,
    report_context: dict | None = None,
):
    st.markdown("### Effectiveness")

    st.markdown("#### First Contact → Outcome")
    render_first_contact_chart(
        records,
        phase,
        report_context=report_context,
    )
    render_effectiveness_table(
        "", records, "first_contact", phase, "First Contact",
        first_contact_table=True,
        show_title=False,
        report_context=report_context,
        report_section_title=(
            "First Contact Effectiveness — Table"
        ),
    )

    st.write("")
    st.markdown("#### Delivery Type Effectiveness")

    if analysis_scope in {
        "Competition Analysis",
        "All Matches Analysis",
    }:
        render_delivery_type_scatter(
            records,
            phase,
            report_context=report_context,
        )

    render_effectiveness_table(
        "",
        records,
        "delivery_type",
        phase,
        "Delivery Type",
        show_title=False,
        report_context=report_context,
        report_section_title=(
            "Delivery Type Effectiveness — Table"
        ),
    )

    st.write("")
    if phase == "offensive":
        render_effectiveness_table(
            "Taker Effectiveness",
            records,
            "taker",
            phase,
            "Taker",
            include_unknown=True,
            report_context=report_context,
        )
    else:
        render_effectiveness_table(
            "Opponent Players Effectiveness",
            records,
            "opponent_players",
            phase,
            "Opponent Players",
            include_unknown=True,
            report_context=report_context,
        )

    st.write("")
    render_effectiveness_table(
        "Side Effectiveness",
        records,
        "side",
        phase,
        "Side",
        report_context=report_context,
    )

    if phase == "offensive":
        st.write("")
        st.markdown("#### Opponent Context")
        render_effectiveness_table(
            "Opponent Organization",
            records,
            "opponent_organization",
            phase,
            "Opponent Organization",
            report_context=report_context,
        )


def build_zone_dataframe(records, zone_key, phase):
    rows = []
    for zone in category_counts(records, zone_key):
        zone_records = records_with_category(records, zone_key, zone)
        m = get_free_kick_metrics(zone_records, phase)
        total = m["total"]

        row = {
            "Zone": zone,
            "Free Kicks": total,
            "FC Won %": calculate_rate(m["fc_won"], total),
            "Attempt %": calculate_rate(m["attempt"], total),
            "Goal %": calculate_rate(m["goal"], total),
            "FC Won": format_rate(m["fc_won"], total),
        }

        if phase == "defensive":
            row.update({
                "Attempt Conceded": format_rate(m["attempt"], total),
                "Goal Conceded": format_rate(m["goal"], total),
                "Goal Conversion": format_rate(m["goal"], m["attempt"]),
            })
        else:
            row.update({
                "Attempt": format_rate(m["attempt"], total),
                "Goal": format_rate(m["goal"], total),
                "Goal Conversion": format_rate(m["goal"], m["attempt"]),
            })

        rows.append(row)

    df = pd.DataFrame(rows)
    if df.empty:
        return df
    return df.sort_values("Free Kicks", ascending=False).reset_index(drop=True)


def render_zone_effectiveness_chart(
    records,
    zone_key,
    phase,
    report_context: dict | None = None,
):
    rows = []
    for zone in category_counts(records, zone_key):
        zone_records = records_with_category(records, zone_key, zone)
        m = get_free_kick_metrics(zone_records, phase)
        total = m["total"]

        metrics = (
            [("FC Won", m["fc_won"]), ("Attempt Conceded", m["attempt"]), ("Goal Conceded", m["goal"])]
            if phase == "defensive"
            else [("FC Won", m["fc_won"]), ("Attempt", m["attempt"]), ("Goal", m["goal"])]
        )

        for metric, count in metrics:
            rows.append({
                "Zone": zone,
                "Metric": metric,
                "Rate": calculate_rate(count, total),
                "Count": count,
                "Total": total,
                "Display": format_rate(count, total),
            })

    df = pd.DataFrame(rows)
    if df.empty:
        return

    fig = px.bar(
        df,
        x="Zone",
        y="Rate",
        color="Metric",
        barmode="group",
        text="Display",
        custom_data=["Count", "Total"],
    )
    fig.update_traces(
        textposition="outside",
        cliponaxis=False,
        hovertemplate=(
            "<b>%{x}</b><br>%{fullData.name}: %{y:.0f}% "
            "(%{customdata[0]}/%{customdata[1]})<extra></extra>"
        ),
    )
    fig.update_layout(
        height=380,
        margin=dict(l=20, r=20, t=10, b=20),
        xaxis_title="",
        yaxis_title="Rate (%)",
        yaxis=dict(range=[0, 118]),
        legend_title="",
    )
    st.plotly_chart(fig, width="stretch")

    if report_context is not None:
        zone_label = (
            "Origin Zone"
            if zone_key == "origin_zone"
            else (
                "Delivery Zone"
                if zone_key == "delivery_zone"
                else "Finishing Zone"
            )
        )

        report_item = create_plotly_report_item(
            module="free_kick",
            section_title=(
                f"{zone_label} Effectiveness"
            ),
            figure=fig,
            context=report_context,
        )

        render_add_to_report_button(
            report_item,
            key=(
                "report_free_kick_zone_chart_"
                f"{zone_key}_"
                f"{report_item['id']}"
            ),
        )


def render_zone_table(
    title,
    records,
    zone_key,
    phase,
    show_title=True,
    report_context: dict | None = None,
    report_section_title: str | None = None,
):
    if show_title:
        st.markdown(f"#### {title}")

    df = build_zone_dataframe(records, zone_key, phase)
    if df.empty:
        st.info("No zone data available.")
        return

    if phase == "defensive":
        display_columns = [
            "Zone", "Free Kicks", "FC Won", "Attempt Conceded", "Goal Conceded", "Goal Conversion"
        ]
    else:
        display_columns = [
            "Zone", "Free Kicks", "FC Won", "Attempt", "Goal", "Goal Conversion"
        ]

    display_df = df[display_columns].copy().rename(
        columns={"Free Kicks": "FKs", "Goal Conversion": "Goal Conv."}
    )

    st.dataframe(
        display_df,
        hide_index=True,
        width="stretch",
        column_config={
            "Zone": st.column_config.TextColumn("Zone", width="large"),
            "FKs": st.column_config.NumberColumn("FKs", width="small"),
        },
    )

    if report_context is not None:
        section_title = (
            report_section_title
            or title
            or (
                "Origin Zone Summary"
                if zone_key == "origin_zone"
                else (
                    "Delivery Zone Summary"
                    if zone_key == "delivery_zone"
                    else "Finishing Zone Summary"
                )
            )
        )

        report_item = create_table_report_item(
            module="free_kick",
            section_title=section_title,
            dataframe=display_df,
            context=report_context,
        )

        render_add_to_report_button(
            report_item,
            key=(
                "report_free_kick_zone_table_"
                f"{zone_key}_"
                f"{report_item['id']}"
            ),
        )


def render_zone_effectiveness(
    records,
    phase,
    report_context: dict | None = None,
):
    st.markdown("### Zone Effectiveness")

    st.markdown("#### Origin Zone Summary")
    render_zone_effectiveness_chart(
        records,
        "origin_zone",
        phase,
        report_context=report_context,
    )
    render_zone_table(
        "",
        records,
        "origin_zone",
        phase,
        show_title=False,
        report_context=report_context,
        report_section_title="Origin Zone Summary",
    )

    st.write("")
    render_zone_table(
        "Delivery Zone Summary",
        records,
        "delivery_zone",
        phase,
        report_context=report_context,
    )

    st.write("")
    render_zone_table(
        "Finishing Zone Summary",
        records,
        "finishing_zone",
        phase,
        report_context=report_context,
    )


def render_free_kick_analysis(
    analysis: dict,
    phase: str | None = None,
    analysis_scope: str | None = None,
    report_context: dict | None = None,
):
    records = analysis.get("records", [])
    if not records:
        st.info("No free-kick events found for the selected filters.")
        return

    phase = resolve_phase(analysis, phase)
    phase_title = "Defensive" if phase == "defensive" else "Offensive"

    st.subheader(f"Free Kicks — {phase_title}")

    render_create_report_button(
        "free_kick",
        key="create_free_kick_report",
    )

    render_kpis(
        records,
        phase,
        report_context=report_context,
    )
    st.markdown("---")

    render_zone_visualisation(
        records,
        report_context=report_context,
    )
    st.markdown("---")

    render_outcome_breakdown(
        records,
        report_context=report_context,
    )
    st.markdown("---")

    render_effectiveness(
        records,
        phase,
        analysis_scope,
        report_context=report_context,
    )
    st.markdown("---")

    render_zone_effectiveness(
        records,
        phase,
        report_context=report_context,
    )
