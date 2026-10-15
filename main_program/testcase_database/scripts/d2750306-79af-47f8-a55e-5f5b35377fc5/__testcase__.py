TESTCASE_NAME = "Patch_Management_LAN_AUTO"
FAMILY_ID = "cb9afed5-66ec-4f51-a50a-ac4d784b502e"

STEPS = [
    ("testcase_database.steps.Resource_Manager.Patch_Management_LAN.list_interfaces", "auto"),
    "testcase_database.steps.Resource_Manager.Patch_Management_LAN.get_interface",
    ("testcase_database.steps.Resource_Manager.Patch_Management_LAN.patch_interface", "auto"),
    "testcase_database.steps.Resource_Manager.Patch_Management_LAN.verify_interface",
]
