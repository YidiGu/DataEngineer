def transform_datatype(form_data):
    form_data = {k: int(v) if str(v).isdigit() else v
                 for k, v in form_data.items()}
    return form_data


def generate_lower_upper_bounds(form_data):
    year_s0 = form_data['Year Sold from']
    year_e0 = form_data['Year Sold until']
    price_s0 = form_data['SalePrice from']
    price_e0 = form_data['SalePrice until']
    return year_s0, year_e0, price_s0, price_e0


def get_logical_expression(form_data):
    salecondition = form_data['SaleCondition']
    g1 = {"YrSold": {"$gte": year_s0}}
    l1 = {"YrSold": {"$lte": year_e0}}
    g2 = {"SalePrice": {"$gte": price_s0}}
    l2 = {"SalePrice": {"$lte": price_e0}}
    if form_data['SaleCondition'] == 'All':
        sc = {'SaleCondition': {'$in': cl.distinct('SaleCondition')}}
    else:
        sc = {'SaleCondition': salecondition}
    return g1, l1, g2, l2, sc  
