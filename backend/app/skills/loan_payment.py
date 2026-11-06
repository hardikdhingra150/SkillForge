"""Fixed monthly payment, total paid and total interest for a loan. Skill source: runs in the sandbox."""


def run(inputs, tools):
    principal, rate, years = float(inputs["principal"]), float(inputs["annual_rate_percent"]), float(inputs["years"])
    if principal <= 0 or years <= 0 or rate < 0:
        raise ValueError("principal and years must be positive and the rate cannot be negative.")
    months = round(years * 12)
    monthly_rate = rate / 100 / 12
    if monthly_rate == 0:
        payment = principal / months
    else:
        payment = principal * monthly_rate / (1 - (1 + monthly_rate) ** -months)
    total = payment * months
    return {"monthly_payment": round(payment, 2), "months": months, "total_paid": round(total, 2),
            "total_interest": round(total - principal, 2)}
