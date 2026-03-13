from my_agents.triage_agent import (
    make_handoff,
    menu_agent,
    order_agent,
    reservation_agent,
    complaints_agent,
)

menu_agent.handoffs = [
    make_handoff(order_agent),
    make_handoff(reservation_agent),
    make_handoff(complaints_agent),
]
order_agent.handoffs = [
    make_handoff(menu_agent),
    make_handoff(reservation_agent),
    make_handoff(complaints_agent),
]
reservation_agent.handoffs = [
    make_handoff(menu_agent),
    make_handoff(order_agent),
    make_handoff(complaints_agent),
]
complaints_agent.handoffs = [
    make_handoff(menu_agent),
    make_handoff(order_agent),
    make_handoff(reservation_agent),
]
