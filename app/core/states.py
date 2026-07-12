"""aiogram FSM state groups for multi-step conversations."""
from aiogram.fsm.state import State, StatesGroup


class AuditStates(StatesGroup):
    waiting_for_channel = State()


class FixStates(StatesGroup):
    waiting_for_channel = State()
