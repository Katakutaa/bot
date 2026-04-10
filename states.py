from aiogram.fsm.state import State, StatesGroup

class OrderState(StatesGroup):
    waiting_for_direction = State()
    waiting_for_requirement_file = State()
    waiting_for_screenshot = State()

class AdminState(StatesGroup):
    waiting_for_order_id_to_approve = State()
    waiting_for_order_id_to_reject = State()
    waiting_for_order_id_for_upload = State()
    waiting_for_completed_file = State()
    waiting_for_reject_reason = State()