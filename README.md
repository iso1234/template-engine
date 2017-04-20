# template-engine
The template engine I made for the NCSS 2017 group 4 project.

To use just download the file and add the following to the top of the python3 file you wish to use it in.
```python
from template-engine import renderTemplate
```
Then you can call the function "renderTemplate".
It takes two arguments:
The first is a filename (string) of the template file you would like to render,
The second is a context dictionary which defines each variable. Each key of the context dictionary needs to be a string.
Please note that the template engine assumes that you have all of your template files in a folder called "templates"
