def generate_portfolio(risk):
    if risk == "保守":
        return {"债券":60, "股票":20, "现金":20}
    elif risk == "稳健":
        return {"债券":40, "股票":40, "现金":20}
    else:
        return {"债券":20, "股票":70, "现金":10}