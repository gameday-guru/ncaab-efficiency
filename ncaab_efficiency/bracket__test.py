import unittest
from typing import TypeVar, Callable, Coroutine, Any
import asyncio
from .bracket import e2e_bracket_by_round, to_rows
from .hardcode import full_example

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

east_example = [
    [["6","92"],None,None,None],
    [None,None,None,None],
    [["33","103"],None,None,None],
    [None,None,None,None],
    [["34","277"],None,None,None],
    [None,None,None,None],
    [["335","27"],None,None,None],
    [None,None,None,None],
    [["113","278"],None,None,None],
    [None,None,None,None],
    [["253","107"],None,None,None],
    [None,None,None,None],
    [["280","134"],None,None,None],
    [None,None,None,None],
    [["109","61"],None,None,None]
]

south_example = [
    [["246","273"],None,None,None],
    [None,None,None,None],
    [["59","110"],None,None,None],
    [None,None,None,None],
    [["245","8"],None,None,None],
    [None,None,None,None],
    [["3","114"],None,None,None],
    [None,None,None,None],
    [["21","100"],None,None,None],
    [None,None,None,None],
    [["250","334"],None,None,None],
    [None,None,None,None],
    [["112","98"],None,None,None],
    [None,None,None,None],
    [["215","111"],None,None,None]
]

midwest_example = [
    [["268","63"],None,None,None],
    [None,None,None,None],
    [["95","44"],None,None,None],
    [None,None,None,None],
    [["275","270"],None,None,None],
    [None,None,None,None],
    [["97","220"],None,None,None],
    [None,None,None,None],
    [["158","94"],None,None,None],
    [None,None,None,None],
    [["145","102"],None,None,None],
    [None,None,None,None],
    [["4","106"],None,None,None],
    [None,None,None,None],
    [["22","7"],None,None,None]
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
    
        res = await e2e_bracket_by_round(full_example)
        print(await to_rows(res))
    