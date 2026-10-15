TESTCASE_NAME = "Indicator_LED_Control_AUTO"
FAMILY_ID = "6ed81a8b-5d54-4340-b68d-b9682a25cd59"

STEPS = [
    "testcase_database.steps.Resource_Chassis.Indicator_LED_Control.get_led",
    ("testcase_database.steps.Resource_Chassis.Indicator_LED_Control.patch_led", "Off"),
    "testcase_database.steps.Resource_Chassis.Indicator_LED_Control.verify_led",
]
