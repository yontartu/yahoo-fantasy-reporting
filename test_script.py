import datetime
import pandas as pd
import bokeh
from bokeh.plotting import figure, output_notebook, show
from bokeh.palettes import Spectral11
from bokeh.models import Legend, LegendItem
from bokeh.models.tools import HoverTool


print('HELLO WORLD!!')
print(datetime.datetime.now())


df = pd.DataFrame({'x': [1, 2, 3, 4], 'y': [.51, .48, .46, .53]})

p = figure(title=f'EXAMPLE, by team',
             x_axis_label='Week',
             y_axis_label='STAT',
             width=800,
             height=400)

xs = df.x.values
ys = df.y.values

r = p.line(xs, ys, 
               line_color='blue', 
               alpha=1, 
               line_width=2)
print('Saving plot...')
bokeh.plotting.output_file('ex_plot.html')
show(p)