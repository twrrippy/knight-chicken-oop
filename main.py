import dotenv
dotenv.load_dotenv()
from main_system.utils.mcp_core import mcp
from main_system.restaurant import restaurant
import controller.admin_controller
import controller.authentication_controller
import controller.booking_controller
import controller.kitchen_controller
import controller.order_controller
import controller.payment_controller
import controller.resource_controller
import controller.simulation_controller
from mock_data import initialize_mock_data

@mcp.tool()
async def get_menu():
    """
    get all food menu details from restaurant
    """
    return restaurant.get_menu()

initialize_mock_data()

if __name__ == "__main__":
    mcp.run()
