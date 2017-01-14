# template-engine
The template engine I made for the NCSS 2017 group 4 project.

To use just download the file and add the following to the top of the python3 file you wish to use it in.
```python
from template import render_template
```
Then you can call the function "render_template".
It takes two arguments:
The first is a filename of the template file you would like to render,
The second is a context dictionary which defines each variable.
