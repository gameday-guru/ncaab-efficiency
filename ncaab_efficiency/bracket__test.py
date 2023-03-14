import unittest
from typing import TypeVar, Callable, Coroutine, Any
import asyncio
from .bracket import e2e_bracket_by_round

AsyncCallable = Callable[..., Coroutine[Any, Any, Any]]

A = TypeVar("A", bound=AsyncCallable)
C = TypeVar("C", bound=Callable)

class DeasyncCallable(Callable):
    bypass : Callable
    
west_example = [
    [["276","141"],None,None,None],
    [None,None,None,None],
    [["105","247"],None,None,None],
    [None,None,None,None],
    [["279","212"],None,None,None],
    [None,None,None,None],
    [["254","108"],None,None,None],
    [None,None,None,None],
    [["93","58"],None,None,None],
    [None,None,None,None],
    [["271","65"],None,None,None],
    [None,None,None,None],
    [["23","101"],None,None,None],
    [None,None,None,None],
    [["31","28"],None,None,None]
]

def deasync(f : A)->C:
    """Transforms an async method into a synchronous one.

    :param f: is the method.
    :type f: A is a AsyncCallable
    :return: the synchronous equivalent of the method.
    :rtype: C is the Callable equivalent of the AsyncCallable.
    """
    def wrapper(*args, **kwargs):
        coro = asyncio.coroutine(f)
        future = coro(*args, **kwargs)
        loop = asyncio.get_event_loop()
        loop.run_until_complete(future)

    wrapper.bypass = f
    return wrapper

class BracketTest(unittest.TestCase):
    """Checks that the get_image_colors methods work appropriately.
    """
    
    @deasync
    async def test_gets_by_round(self):
    
        await e2e_bracket_by_round(west_example)
    