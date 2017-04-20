import re
import html # Used to stop html injections
import copy # Used to make deepcopys of dictionarys


def renderTemplate(filename:str, context:dict):
    """ Renders HTML from a template file """
    # Get template string
    with open("templates/" + filename, encoding='utf-8') as f:
        template = f.read()
        template = template.replace('“', '"') # Removes smart quotes
        template = template.replace('”', '"') # Ditto
    context = copy.deepcopy(context)
    # Parse the template string and create node tree
    tree = parse(template)
    # Render the node tree and return the result
    return render(tree, context)


def parse(template:str):
    """ Checks the syntax of the template file 'template'
        and creates and returns a node tree """
    lex = Lexer(template) # Create lexer object and pass it the template string
    nodeTree = lex.parse() # Call the parse method that will parse the string and return a node tree
    return nodeTree


def render(nodeTree:object, context:dict):
    """ Calls the .render() method on the head of the node tree """
    return nodeTree.render(context)


def getNodeType(string:str):
    """ Returns what type of node 'string' starts with """
    if re.match(r'{{.*}}', string) is not None: # Check if is a python expression tag
        return "python"
    elif re.match(r'{% *include.*%}', string) is not None: # Check if its an include tag
        return "include"
    elif re.match(r'{% *let.*%}', string) is not None: # Check if its an let tag
        return "let"
    elif re.match(r'{% *safe.*%}', string) is not None: # Check if its an safe tag
        return "safe"
    elif re.match(r'{% *if.*%}.*{% *end *if *%}', string, re.DOTALL) is not None: # Check if its a pair of 'if' tags
        return "if"
    elif re.match(r'{% *comment *%}.*{% *end *comment *%}', string, re.DOTALL) is not None: # Check if its a pair of 'if' tags
        return "comment"
    elif re.match(r'{% *for.*in.*%}.*{% *end *for *%}', string, re.DOTALL) is not None: # Check if its a pair of 'for' tags
        return "for"
    # The following two conditions are used in parseIf() and parseFor() but ignored in parse()
    elif re.match(r'{% *end *for *%}', string) is not None: # Check if its an 'end for' tag
        return "endfor"
    elif re.match(r'{% *end *if *%}', string) is not None: # Check if its an 'end if' tag
        return "endif"
    # This is used in parseIf() but ignored in parse()
    elif re.match(r'{% *else *%}', string) is not None:
        return "else"
    # This is used in parseFor() but ignored in parse()
    elif re.match(r'{% *empty *%}', string) is not None:
        return "empty"
    else:
        return "text"


class Lexer: # This checks the syntax and creates a node tree
    def __init__(self, template:str):
        self.template = template
        self.upto = 0
        self.nodeTree = GroupNode() # Head node of the tree

    def peek(self, amt=1):
        """ Returns the next 'amt' character (Returns none if thats past the end of the string) """
        if self.upto+amt-1 < len(self.template):
            return self.template[self.upto:self.upto+amt]

    def next(self):
        self.upto += 1

    def parse(self):
        """ Parses self.template and returns a node tree """
        nodeTree = GroupNode()
        while self.upto < len(self.template): # While there's still input left
            nodeType = getNodeType(self.template[self.upto:])
            if nodeType in ["text", "endif", "endfor", "else", "empty"]:
                nodeTree.children.append(self.parseText())
            elif nodeType == "python":
                nodeTree.children.append(self.parsePython())
            elif nodeType == "include":
                nodeTree.children.append(self.parseInclude())
            elif nodeType == "let":
                nodeTree.children.append(self.parseLet())
            elif nodeType == "safe":
                nodeTree.children.append(self.parseSafe())
            elif nodeType == "comment":
                self.parseComment()
            elif nodeType == "if":
                nodeTree.children.append(self.parseIf())
            elif nodeType == "for":
                nodeTree.children.append(self.parseFor())
        return nodeTree

    def parseText(self, flag=""):
        """ This parses a text node. This will continue to parse until it finds another node. 
            This function usually treats nodes of type "endif" and "endfor" as plain text. When
            the flag argument is set to either of these values it will stop pasing when it reaches
            a node of said type. This is useful when parsing an if or for block. """
        start = self.upto
        # While its not the start of another node or the end of the string
        nodeType = getNodeType(self.template[self.upto:])
        while nodeType == "text" and nodeType != flag and self.peek() is not None:
            self.next()
            nodeType = getNodeType(self.template[self.upto:])
        # Return text node object
        return TextNode(self.template[start:self.upto])

    def parsePython(self):
        start = self.upto
        while self.peek(2) != "}}": # While its not the end of the node
            self.next()
        # Skip the ending brackets
        self.next()
        self.next()
        # Return python node object
        return PythonNode(self.template[start:self.upto])

    def parseInclude(self):
        start = self.upto
        while self.peek(2) != "%}": # While its not the end of the node
            self.next()
        # Skip the ending '%}'
        self.next()
        self.next()
        # Return an include object
        return IncludeNode(self.template[start:self.upto])

    def parseLet(self):
        start = self.upto
        while self.peek(2) != "%}": # While its not the end of the node
            self.next()
        # Skip the ending '%}'
        self.next()
        self.next()
        # Return a let object
        return LetNode(self.template[start:self.upto])

    def parseSafe(self):
        start = self.upto
        while self.peek(2) != "%}": # While its not the end of the node
            self.next()
        # Skip the ending '%}'
        self.next()
        self.next()
        # Return a safe object 
        return SafeNode(self.template[start:self.upto])
        
    def parseComment(self):
        start = self.upto
        # Look for the start of the {% end comment %} tag
        while re.match(r'{% *end *comment *%}', self.template[self.upto:]) is not None:
            self.next()
        # Look for the end of the {% end comment %} tag
        while self.peek(2) != "%}":
            self.next()
        # Skip the ending '%}'
        self.next()
        self.next()

    def parseIf(self):
        """ This parses an if node. It uses a version of parse() to parse the
            inner code block. This is different from the parse function because 
            the flag "endif" is used when calling the parseText() function to 
            stop it treating the end if tag as plain text. This version of 
            parse() also deals with "else" nodes. """
        ifNodeObject = IfNode()
        start = self.upto
        # Look for the end of the 'if' tag
        while self.peek(2) != "%}":
            self.next()
        self.next()
        self.next()
        # Add the 'if' tag to the ifNode object
        ifNodeObject.ifTag = self.template[start:self.upto]
        # Create objects and add them to the ifNodeObject's children list
        while re.match(r'{% *end *if *%}', self.template[self.upto:]) is None and self.peek():
            nodeType = getNodeType(self.template[self.upto:])
            if nodeType == "python":
                ifNodeObject.children.append(self.parsePython())
            elif nodeType == "include":
                ifNodeObject.children.append(self.parseInclude())
            elif nodeType == "let":
                ifNodeObject.children.append(self.parseLet())
            elif nodeType == "if":
                ifNodeObject.children.append(self.parseIf())
            elif nodeType == "for":
                ifNodeObject.children.append(self.parseFor())
            elif nodeType == "text":
                ifNodeObject.children.append(self.parseText("endif"))
            elif nodeType == "safe":
                ifNodeObject.children.append(self.parseSafe())
            elif nodeType == "comment":
                self.parseComment()
            elif nodeType == "else":
                self.parseElse()
                ifNodeObject.children.append("else")
        if self.peek() is None:
            raise SyntaxError("Unexpected EOF while parsing.\n \
            This is possibly caused by the absence of an {% end if %} tag")
        # Look for the end of the {% end if %} tag
        while self.peek(2) != "%}":
            self.next()
        # Skip the ending '%}'
        self.next()
        self.next()
        # Return an if object
        return ifNodeObject
        
    def parseElse(self):
        # Look for the end of the {% else %} tag
        while self.peek(2) != "%}":
            self.next()
        # Skip the ending '%}'
        self.next()
        self.next()
    
    def parseEmpty(self):
        # Look for the end of the {% empty %} tag
        while self.peek(2) != "%}":
            self.next()
        # Skip the ending '%}'
        self.next()
        self.next()

    def parseFor(self):
        """ This parses an for node. It uses a version of parse() to parse the
            inner code block. This is different from the parse function because 
            the flag "endfor" is used when calling the parseText() function to 
            stop it treating the end for tag as plain text. This version of 
            parse() also deals with "empty" nodes. """
        forNodeObject = ForNode()
        start = self.upto
        # Look for the end of the 'for' tag
        while self.peek(2) != "%}":
            self.next()
        self.next()
        self.next()
        # Add the 'for' tag to the forNode object
        forNodeObject.forTag = self.template[start:self.upto]
        # Create objects and add them to the forNodeObject's children list
        while re.match(r'{% *end *for *%}', self.template[self.upto:]) is None and self.peek() is not None:
            nodeType = getNodeType(self.template[self.upto:])
            if nodeType == "python":
                forNodeObject.children.append(self.parsePython())
            elif nodeType == "include":
                forNodeObject.children.append(self.parseInclude())
            elif nodeType == "let":
                forNodeObject.children.append(self.parseLet())
            elif nodeType == "if":
                forNodeObject.children.append(self.parseIf())
            elif nodeType == "for":
                forNodeObject.children.append(self.parseFor())
            elif nodeType == "text":
                forNodeObject.children.append(self.parseText("endfor"))
            elif nodeType == "safe":
                forNodeObject.children.append(self.parseSafe())
            elif nodeType == "comment":
                self.parseComment()
            elif nodeType == "empty":
                self.parseElse()
                forNodeObject.children.append("empty")
        # If it didn't find a closing tag
        if self.peek() is None:
            raise SyntaxError("Unexpected EOF while parsing.\n \
            This is possibly caused by the absence of an {% end for %} tag")
        # Look for the end of the {% end for %} tag
        while self.peek(2) != "%}":
            self.next()
        # Skip the ending '%}'
        self.next()
        self.next()
        # Return an for object
        return forNodeObject


class GroupNode:
    def __init__(self, children=None):
        if children == None:
            self.children = []
        else:
            self.children = children
        self.output = []

    def render(self, context:dict):
        output = []
        for child in self.children:
            output.append(str(child.render(context)))
        return "".join(output)


class PythonNode:
    def __init__(self, content):
        self.content = content
        self.content = self.content[2:-2].strip()

    def render(self, context):
        try:
            return html.escape(str(eval(self.content, {}, context)))
        except NameError: # If there is an unknown variable
            return ""


class SafeNode:
    def __init__(self, content):
        self.content = content

    def render(self, context):
        self.content = self.content[2:-2].replace("safe", "").strip()
        try:
            return eval(self.content, {}, context)
        except NameError: # If there is an unknown variable
            return ""


class TextNode:
    def __init__(self, content):
        self.content = content

    def render(self, context):
        return self.content


class IncludeNode:
    def __init__(self, content):
        self.content = content

    def render(self, context):
        # Create a string for the file name and a string for the arguments (variable assignments)
        fileName, *argumentString = self.content[2:-2].replace("include", "", 1).strip().split(" ")
        argumentString = " ".join(argumentString)
        # Remove any quotation marks
        fileName = fileName.strip("'").strip('"')
        # Split the arguments up
        arguments = []
        match = re.match(r'( *\w* *= *\w*)', argumentString)
        while match is not None:
            arguments.append(match.group(1).replace(" ", ""))
            argumentString = argumentString[len(match.group(1)):]
            match = re.match(r'( *\w* *= *\w*)', argumentString)
        # Call the file with the new arguments (if there are any)
        newContext = copy.deepcopy(context)
        if len(arguments) >= 1:
            for variable in arguments:
                key, value = variable.split("=")
                newContext[key] = eval(value, {}, context)
        return renderTemplate(fileName, newContext)


class LetNode:
    def __init__(self, content):
        self.content = content

    def render(self, context):
        var, expression = self.content[2:-2].replace("let", "").strip().split("=")
        context[var.strip()] = eval(expression, {}, context)
        return ""


class IfNode:
    def __init__(self):
        self.ifTag = ""
        self.children = []

    def render(self, context):
        ifTrue = [] # Will be returned if the condition is true
        ifFalse = []# Will be returned if the condition is false
        # Evaluate the condition
        try:
            condition = eval(self.ifTag[2:-2].replace("if", "").strip(), {}, context)
        except NameError: # If a variable in the condition isn't defined
            condition = False
        # Check for an else node
        if "else" in self.children:
            index = self.children.index("else")
            ifTrue = self.children[:index]
            ifFalse = self.children[index+1:]
        else:
            ifTrue = self.children
        # Render
        output = []
        if condition:
            for child in ifTrue:
                output.append(str(child.render(context)))
        else:
            for child in ifFalse:
                output.append(str(child.render(context)))
        return "".join(output)
        
        
class ForNode:
    def __init__(self):
        self.forTag = ""
        self.children = []
        
    def render(self, context):
        ifNotEmpty = []
        ifEmpty = []
        # Split the for node into the iterable and the variables
        variables, iterable = self.forTag[2:-2].replace("for", "").split("in")
        variables = variables.split(",")
        try:
            iterable = eval(iterable, {}, context)
        except NameError: # If a variable in the iterable isn't defined
            return ""
        # Check for tuple/string/list unpacking
        if len(variables) > 1:
            for item in iterable:
                if len(item) != len(variables):
                    return ""
        # Check for an empty node
        if "empty" in self.children:
            index = self.children.index("empty")
            ifNotEmpty = self.children[:index]
            ifEmpty = self.children[index+1:]
        else:
            ifNotEmpty = self.children
        # Render
        output = []
        if iterable:
            for item in iterable:
                # If tuple/list/string unpacking needs to be dealt with
                if len(variables) > 1:
                    # Add multiple new variables to the context
                    newContext = copy.deepcopy(context)
                    for index, var in enumerate(variables):
                        newContext[var.strip()] = item[index]
                # If tuple/list/string unpacking doesn't need to be dealt with
                else:
                    # Add the new variable to the context
                    newContext = copy.deepcopy(context)
                    newContext[variables[0].strip()] = item
                # Render each node in the codeblock with the new context
                for child in ifNotEmpty:
                    output.append(child.render(newContext))
        # If the iterable is empty
        else:
            for child in ifEmpty:
                output.append(str(child.render(context)))
        return "".join(output)