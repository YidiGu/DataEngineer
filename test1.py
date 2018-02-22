# -*- coding: utf-8 -*-
"""
Created on Thu Jan 25 16:34:29 2018

@author: Yidi Gu
"""
# Get the package
import flask  # web interface
import pandas as pd
# bokeh for plotting
from bokeh.plotting import figure, ColumnDataSource
from bokeh.embed import components
from bokeh.models import HoverTool
from flask import Flask, render_template, request
from gevent.wsgi import WSGIServer

import util
from util import get_formdata
import seach
import getfigure

# call the mongo database
cl, cl_full, field_description, cl_currency = util.call_mongoDB()

# build web interface
app = Flask(__name__)


@app.route("/")
def main():
    env = {
        'tablename': 'House Prices',
        'columns': list(cl.find_one())[1:],
        'data': cl.find().limit(20),
        'saletype_option': cl.distinct('SaleType'),
        'salecondition_option': cl.distinct('SaleCondition'),
        'currency_option': cl_currency.distinct('currency'),
        'field_description': list(field_description.find())
    }
    return render_template('index.html', **env)


@app.route("/new_data", methods=['POST'])
def new_data():
    form_data = get_formdata(request.form)
    form_data = util.create_dataframe_with_currency(cl, cl_currency, form_data)
    # insert data into database
    cl.insert_one(form_data)
    # set variable
    env = {
        'tablename': 'New inserted data',
        'columns': list(cl.find_one())[1:],
        'data': form_data,
        'saletype_option': cl.distinct('SaleType'),
        'salecondition_option': cl.distinct('SaleCondition')
    }
    return render_template('new_data.html', **env)


@app.route("/search", methods=['POST'])
def search():
    form_data = get_formdata(request.form)
    # transform data type
    form_data = seach.transform_datatype(form_data)
    # JSON logical expression preparing with lower and upper bounds
    g1, l1, g2, l2, sc = seach.get_logical_expression(form_data)
    # Get logical relation
    emptykey = util.empty_keys(form_data)
    log1, log2, log3, log4 = seach.get_logical_relation(emptykey)
    # request data from database
    lookup = cl.find({
            log4: [{
                    log3: [{log1: [g1, l1]}, {log2: [g2, l2]}]}, sc]})
    env = {
        'tablename': 'Searching',
        'columns': list(cl.find_one())[1:],
        'data': lookup,
        'requests': util.remove_empty(form_data, emptykey),
        'requests_len': lookup.count()
    }
    return render_template('search.html', **env)


@app.route("/exchange", methods=['POST'])
def exchange():
    form_data = get_formdata(request.form)
    # print(form_data)
    target_currency = form_data['currency']
    # get the exchange rate from database
    exchange_rate = list(cl_currency.find({
            'currency': target_currency}))[0]['rate']
    lookup = list(cl.aggregate(util.exchange_pipeline(exchange_rate)))
    required_data_lenth = len(lookup)
    # set up parameter
    env = {
        'tablename': 'Searching',
        'columns': lookup[:1][0].keys(),
        'data': lookup,
        'requests': form_data,
        'selected_currency': target_currency,
        'requests_len': required_data_lenth
    }
    return render_template('search.html', **env)


@app.route("/getfigure", methods=['POST'])
def prepare_figure():
    form_data = get_formdata(request.form)
    axis = util.get_form(form_data)
    # use regular expression to find the field correlated to the date
    field_date = getfigure.get_date_related_fields_name(field_description)
    # find the field is categorical data, $type is str
    field_categorical = getfigure.get_categorical_fields_name(cl_full)
    # Some general set up
    tool = 'pan,wheel_zoom,box_zoom,reset,previewsave,hover'
    title = axis.x_label+' vs '+axis.y_label
    x_axis_type = 'linear'
    x_range = None
    # prepare for the figure
    # if axis.x_label in 'MoYrSold':
    if axis.x_label == 'MoYrSold':
        # merge month and year
        tmp = getfigure.aggregate_merge_month_year(cl_full, axis)
        title = 'Sold time vs '+axis.y_label
        x_axis_type = 'datetime'
        axis.x_label = 'Month and Year Sold'
        date = ['year', 'month']
        df = getfigure.prepare_df_time(tmp, axis, date)
        p = getfigure.figure_setting(title, tool, axis, x_axis_type, x_range)
        p.line('x', 'y', source=ColumnDataSource(df))
        getfigure.hovertools_settings(fig = p, x_type = x_axis_type)
    # elif form in field_date:
    elif axis.x_label in field_date:
        # transfer the int to date
        tmp = getfigure.aggregate_avg_sale(cl_full, axis)
        x_axis_type = 'datetime'
        date = ['_id']
        df = getfigure.prepare_df_time(tmp, axis, date)
        p = getfigure.figure_setting(title, tool, axis, x_axis_type, x_range)
        p.line('x', 'y', source=ColumnDataSource(df))
        getfigure.hovertools_settings(fig = p, x_type = x_axis_type)

    # elif form in field_categorical:
    elif axis.x_label in field_categorical:
        # 1. categorcial axis 2. boxplot(later)
        tmp = getfigure.aggregate_avg_sale(cl_full, axis)
        factor = []
        y = []
        for i in tmp:
            factor.append(i['_id'])
            y.append(i[axis.y_title])
        # replace MoSold with month name
        if axis.x_label == 'MoSold':
            factor = [util.NumToMonth(i) for i in factor]
        p = figure(tools=tool, x_range=factor, title=title)
        p.xaxis.axis_label = axis.x_label
        p.yaxis.axis_label = axis.y_label
        # p = prepare_figure(title,tool,axis,x_axis_type,x_range)
        p.circle(factor, y, size=15,
                 source=ColumnDataSource(pd.DataFrame(
                         dict(factor=factor, y=y))))
        getfigure.hovertools_settings(fig = p, x = axis.x_label,
        tip_col = '@factor')

    # else:
    else:
        # simple calculate the averge:
        tmp = getfigure.aggregate_avg_sale(cl_full, axis)
        x = []
        y = []
        for i in tmp:
            x.append(i['_id'])
            y.append(i[axis.y_title])
        title = axis.x_label+' vs '+axis.y_label
        p = getfigure.figure_setting(title, tool, axis, x_axis_type, x_range)
        p.line(x, y, line_width=2, source=ColumnDataSource(
                pd.DataFrame(dict(x=x, y=y))))
        getfigure.hovertools_settings(fig = p, x = axis.x_label,
        tip_col = '@x')
    # get html components
    script, div = components(p)
    env = {
        'script': script,
        'div': div}

    return render_template('get_figure.html', **env)


@app.route("/addfigure", methods=['POST'])
def plot_figure():
    form_data = get_formdata(request.form)
    print(form_data)
    target_currency = form_data['currency']
    exchange_rate = list(cl_currency.find({
            'currency': target_currency}))[0]['rate']
    lookup = list(cl.aggregate(util.exchange_pipeline(exchange_rate)))
    required_data_lenth = len(lookup)
    tmp = cl.aggregate([{
            '$group': {'_id': '$YrSold', 'avgPrice': {'$avg': '$SalePrice'}}
            }, {'$sort': {'_id': 1}}])
    x = []
    y = []
    for i in tmp:
        x.append(i['_id'])
        y.append(i['avgPrice'])
    # create a new plot with a title and axis labels
    p = figure(title="YrSold vs SalePrice",
               x_axis_label='Year Sold',
               y_axis_type='log',
               y_axis_label='Sale Price')
    # add a line renderer with legend and line thickness
    p.line(x, y, legend="Sale Price", line_width=2)
    script, div = components(p)
    env = {
        'tablename': 'Searching',
        'columns': lookup[:1][0].keys(),
        'data': lookup,
        'requests': form_data,
        'selected_currency': target_currency,
        'requests_len': required_data_lenth,
        'script': script,
        'div': div}
    return render_template('add_figure.html', **env)


@app.route("/requestfile", methods=['POST'])
def save_excel():
    form_data = dict(request.form)
    # print(form_data)
    target_currency = form_data['currency'][0]
    exchange_rate = list(cl_currency.find({
            'currency': target_currency}))[0]['rate']
    data = list(cl.aggregate(util.exchange_pipeline(exchange_rate)))
    title = 'House Pirce in ' + target_currency
    mimetype = 'application/vnd.openxmlformats-officedocument.\
    spreadsheetml.sheet'
    response = flask.Response(util.prepareExcel(data, title),
                              mimetype=mimetype)
    response.headers['Content-Type'] = mimetype
    filename = 'attachment; filename=House Price ( '+target_currency+' ).xlsx'
    response.headers['Content-Disposition'] = filename
    return response


if __name__ == "__main__":

    wsgiserverX = WSGIServer(('0.0.0.0', 8080), app)
    print("Started")
    wsgiserverX.serve_forever()
