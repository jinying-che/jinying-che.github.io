---
title: "Python Cheatsheet"
date: "2023-01-31T11:40:49+08:00"
tags: ["python", "cheatsheet"]
description: "Python best practice and some pitfalls"
---

### Pass By Reference 
1. Python passes arguments neither by reference nor by value, but by assignment. The parameter passed in is actually a reference to an object (but the reference is passed by value)
	```python
	def main():
	    n = 9001
	    print(f"[main] before n: {hex(id(n))} # same")
	    increment(n)
	    print(f"[main] after  n: {hex(id(n))} # same")
	
	def increment(x):
	    print(f"[func] before x: {hex(id(x))} # same")
	    x += 1
	    print(f"[func] after  x: {hex(id(x))} # address altered after the assignment")
	
	main()
	
	# output
	[main] before n: 0x11035a0b0 # same
	[func] before x: 0x11035a0b0 # same
	[func] after  x: 0x11035a190 # address altered after the assignment
	[main] after  n: 0x11035a0b0 # same
	```

2. Mutability, an object is **mutable** if its structure can be changed in place rather than requiring reassignment.
	> If you pass a mutable object into a method, the method gets a reference to that same object and you can mutate it to your heart's delight, but if you rebind the reference in the method, the outer scope will know nothing about it, and after you're done, the outer reference will still point at the original object.

	The followings are the mutable objects in Python: 
	- Dictionary
	  ```python
	  # Dictionaries are mapping types.
	  mt = {"n": 4}
	  # Define a function to operate on a key:
	  def square(num_dict):
	      num_dict["n"] *= num_dict["n"]
	  
	  square(mt)
	  mt
	  # output: 16
	  ```
	- List
	  ```python
	  # Lists are both subscriptable and mutable.
	  sm = [4]
	  # Define a function to operate on an index:
	  def square(num_list):
	      num_list[0] *= num_list[0]
	  
	  square(sm)
	  sm
	  # output: [16]
	  ```
	- Object Attributes
	  ```python
	  # For the purpose of this example, let's use SimpleNamespace.
	  from types import SimpleNamespace
	  
	  # SimpleNamespace allows us to set arbitrary attributes.
	  # It is an explicit, handy replacement for "class X: pass".
	  ns = SimpleNamespace()
	  
	  # Define a function to operate on an object's attribute.
	  def square(instance):
	      instance.n *= instance.n
	  
	  ns.n = 4
	  square(ns)
	  ns.n
	  # output: 16
	  ```


### Reference
- [Pass by Reference in Python: Background and Best Practices](https://realpython.com/python-pass-by-reference/#toc)
- [How do I write a function with output parameters (call by reference)?](https://docs.python.org/3/faq/programming.html#how-do-i-write-a-function-with-output-parameters-call-by-reference)
