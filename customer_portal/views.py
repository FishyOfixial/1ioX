from django.shortcuts import get_object_or_404, render

from customer_portal.decorators import customer_required
from customer_portal.services.sim_service import get_client_sims
from customer_portal.translations import LANG_PORTAL


@customer_required
def customer_dashboard(request):
    lang = LANG_PORTAL.get(request.user.preferred_lang, LANG_PORTAL["es"])
    sims = get_client_sims(request.user)
    query = (request.GET.get("q") or "").strip()
    selected_sub_status = (request.GET.get("sub_status") or "").strip()

    if query:
        sims = sims.filter(iccid__icontains=query)

    sim_cards = []
    for sim in sims:
        subscription = sim.current_subscription
        status_key = subscription.status if subscription else None

        if selected_sub_status:
            if selected_sub_status == "none" and subscription is not None:
                continue
            if selected_sub_status != "none" and status_key != selected_sub_status:
                continue

        sim_cards.append(
            {
                "sim": sim,
                "subscription": subscription,
                "sim_status_label": lang["sim_states"].get(sim.status, sim.status),
                "subscription_status_key": status_key,
                "subscription_status_label": (
                    lang["subscription_states"].get(status_key, status_key)
                    if status_key
                    else "-"
                ),
            }
        )

    return render(
        request,
        "customer_portal/dashboard.html",
        {
            "sim_cards": sim_cards,
            "lang": lang,
            "current_lang": request.user.preferred_lang,
            "q": query,
            "selected_sub_status": selected_sub_status,
        },
    )


@customer_required
def customer_sim_detail(request, sim_id):
    lang = LANG_PORTAL.get(request.user.preferred_lang, LANG_PORTAL["es"])
    sims = get_client_sims(request.user)
    sim = get_object_or_404(sims, id=sim_id)
    subscription = sim.current_subscription
    status_key = subscription.status if subscription else None
    data_quota = sim.quotas.filter(quota_type="DATA").first()
    sms_quota = sim.quotas.filter(quota_type="SMS").first()

    return render(
        request,
        "customer_portal/sim_detail.html",
        {
            "sim": sim,
            "sim_status_label": lang["sim_states"].get(sim.status, sim.status),
            "subscription": subscription,
            "subscription_status_key": status_key,
            "subscription_status_label": (
                lang["subscription_states"].get(status_key, status_key)
                if status_key
                else lang["no_subscription"]
            ),
            "lang": lang,
            "current_lang": request.user.preferred_lang,
            "data_quota": data_quota,
            "sms_quota": sms_quota,
        },
    )
