from typing import TypedDict, Literal, Optional
from backend.agents.zillow_agent import ZillowAgentState
import os
import requests
from dotenv import load_dotenv
import httpx
import asyncio

GEOCLIENT_URL = "https://api.nyc.gov/geoclient/v2/search"
VIOLATIONS_URL = "https://data.cityofnewyork.us/resource/wvxf-dwi5.json"
AEP_URL = "https://data.cityofnewyork.us/resource/hcir-3275.json"
CHARGES_URL = "https://data.cityofnewyork.us/resource/mdbu-nrqn.json"
LITIGATION_URL = "https://data.cityofnewyork.us/resource/59kj-x8nc.json"
ORDERS_URL = "https://data.cityofnewyork.us/resource/tb8q-a3ar.json"
NOT_LANDLORD_FAULT_REASONS = [
    "duplicate omo",
    "utility account picked up by esb",
    "vacant land",
    "apt. vacant",
    "bldg. vacant",
    "user error",
    "condition not found",
    "condition does not exist",
    "for field visits only - cancelled", ]

class ViolationRecord(TypedDict):
    violationid: str
    class_: str
    novdescription: str
    inspectiondate: str
    violationstatus: str
    rentimpairing: bool


class EnforcementRecord(TypedDict):
    source: Literal["AEP", "Charges", "Litigation", "Order"]
    date: str
    description: str
    is_active: bool                    # Meaningful for AEP/Litigation/Order. Always False for Charges (no in-progress concept)
    is_landlord_fault: Optional[bool]     # Only meaningful for Charges (based on OMOStatusReason). None for other sources
    amount: Optional[float]           # Only Charges has a value. None for other sources


class HPDAgentState(ZillowAgentState):
    bbl: str  
    geocoding_success: bool
    hpd_violations: list[ViolationRecord]              # Raw violation records from Violation Files
    hpd_enforcement_records: list[EnforcementRecord]    # Combined AEP/Charges/Litigation/Order records
    violation_score: float                              # Aggregated severity score from violations
    enforcement_score: float                            # Aggregated severity score from enforcement records
    violations_fetch_success: bool                      # Whether the violation API call succeeded
    enforcement_fetch_success: bool                     # Whether the enforcement API calls succeeded
    hpd_severity_label: Literal["good", "caution", "danger"]   # Final severity label based on total_score

class HPDVerdictExplanation(TypedDict):
    severity_explanation: str
    negotiation_comment: str

def geocode_address(state: HPDAgentState) -> HPDAgentState: # 사용자가 입력한 자유 텍스트 주소로, Geoclient API 호출. 정확한 bbl 숫자 하나로 이후 5개 노드가 조회됨. 이후 fetch_violations, fetch_enforcement,..
    print(f"Received input: {state['address']}")

    try:
        api_key=os.getenv("GEOCLIENT_APP_KEY")
        params = {"input": state["address"]}
        headers = {"Ocp-Apim-Subscription-Key": api_key}
        response = requests.get(GEOCLIENT_URL, params = params, headers = headers)
        response.raise_for_status()
        data = response.json()

        bbl = data["results"][0]["response"]["bbl"]

                
    except requests.exceptions.RequestException as e:
        print(f"API call failed: {e}")
        return HPDAgentState(geocoding_success=False)


    return HPDAgentState(bbl=bbl, geocoding_success=True)

def fetch_violations(state: HPDAgentState) -> HPDAgentState: 
    print(f"Received input: {state['bbl']}")
    try:
        params = {"$where": f"bbl = '{state['bbl']}'"}
        response = requests.get(VIOLATIONS_URL, params = params)
        response.raise_for_status()
        data = response.json()

        violations = []

        for c in data:
            violation = {"violationid": c["violationid"], "class_": c["class"],
            "novdescription": c["novdescription"], "inspectiondate": c["inspectiondate"], 
            "violationstatus": c["violationstatus"],  "rentimpairing": c["rentimpairing"]}
            violations.append(violation)
                                      
    except requests.exceptions.RequestException as e:
        print(f"API call failed: {e}")
        return HPDAgentState(violations_fetch_success=False)


    return HPDAgentState(hpd_violations=violations, violations_fetch_success=True)

async def fetch_aep(bbl):
    async with httpx.AsyncClient() as client:
        params = {"$where": f"bbl = '{bbl}'"}
        response = await client.get(AEP_URL, params = params)
        response.raise_for_status()
        data = response.json()
        return data

async def fetch_charges(bbl):
    async with httpx.AsyncClient() as client:
        params = {"$where": f"bbl = '{bbl}'"}
        response = await client.get(CHARGES_URL, params = params)
        response.raise_for_status()
        data = response.json()
        return data

async def fetch_litigations(bbl):
    async with httpx.AsyncClient() as client:
        params = {"$where": f"bbl = '{bbl}'"}
        response = await client.get(LITIGATION_URL, params = params)
        response.raise_for_status()
        data = response.json()
        return data

async def fetch_orders(bbl):
    async with httpx.AsyncClient() as client:
        params = {"$where": f"bbl = '{bbl}'"}
        response = await client.get(ORDERS_URL, params = params)
        response.raise_for_status()
        data = response.json()
        return data

async def fetch_enforcement(state: HPDAgentState) -> HPDAgentState: 
    print(f"Received input: {state['bbl']}")
    
    results = await asyncio.gather(
        fetch_aep(state["bbl"]),
        fetch_charges(state["bbl"]),
        fetch_litigations(state["bbl"]),
        fetch_orders(state["bbl"]),
        return_exceptions=True,
        )

    enforcement_records = []
    all_ok = True

    aep_result = results[0]
    if isinstance(aep_result, Exception):
        print(f"AEP failed: {aep_result}")
        all_ok = False
    else:
        for c in aep_result:
            record = {"source": "AEP",  
                      "date": c["aep_start_date"], 
                      "description": f"Selected for AEP with {c['of_b_c_violations_at_start']} B/C violations at start", 
                      "is_active":c["current_status"] == "AEP Active", 
                      "is_landlord_fault": None, 
                      "amount": None}
            enforcement_records.append(record)

    charges_result = results[1]
    if isinstance(charges_result, Exception):
        print(f"Charges failed: {charges_result}")
        all_ok = False
    else:
        for c in charges_result:
            record = {"source": "Charges",  
                      "date": c["omocreatedate"], 
                      "description": c["omodescription"],
                      "is_active": False, 
                      "is_landlord_fault": c.get("omostatusreason", "").lower() not in NOT_LANDLORD_FAULT_REASONS, 
                      "amount": float(c["omoawardamount"]) if "omoawardamount" in c else None,}
            enforcement_records.append(record)

    litigation_result = results[2]
    if isinstance(litigation_result, Exception):
        print(f"Litigation failed: {litigation_result}")
        all_ok = False
    else:
        for c in litigation_result:
            record = {"source": "Litigation",  
                        "date": c["caseopendate"], 
                        "description": f"Housing litigation: {c['casetype']}",
                        "is_active": c["casestatus"] == "PENDING", 
                        "is_landlord_fault": None, 
                        "amount": None,}
            enforcement_records.append(record)

    orders_result = results[3]
    if isinstance(orders_result, Exception):
        print(f"Order failed: {orders_result}")
        all_ok = False
    else:
        for c in orders_result:
            record = {"source": "Order",
                      "date": c["vacate_effective_date"],
                      "description": f"Vacate order ({c['vacate_type']}): {c['primary_vacate_reason']}",
                      "is_active": "actual_rescind_date" not in c,
                      "is_landlord_fault": None,
                      "amount": None}
            enforcement_records.append(record)

    return HPDAgentState(hpd_enforcement_records = enforcement_records, enforcement_fetch_success=all_ok)
        

   
    

    

# if __name__ == "__main__":
#     test_state = HPDAgentState(address="776 Franklin Ave, Brooklyn, NY, 11238")
#     result = geocode_address(test_state)
#     print(result)

# if __name__ == "__main__":
#     test_state = HPDAgentState(address="2 North 6 Place, Brooklyn, NY, 11249")
#     result = geocode_address(test_state)
#     print(result)


# if __name__ == "__main__":
#     test_state = HPDAgentState(bbl="3023240030")
#     result = fetch_violations(test_state)
#     print(result)

# if __name__ == "__main__":
#     async def test():
#         result = await fetch_aep("2027627501")
#         print("AEP:", result)
#         result = await fetch_charges("2031530041")
#         print("CHARGES:", result)
#         result = await fetch_litigations("1008960023")
#         print("LITIGATIONS:", result)
#         result = await fetch_orders("4098030009")
#         print("ORDERS:", result)
        
#     asyncio.run(test())
    
    
# if __name__ == "__main__":
#     async def sample_test():
#         urls = {"CHARGES" : CHARGES_URL}

#         async with httpx.AsyncClient() as client:
#             for name, url in urls.items():
#                 response = await client.get(url, params =  {"$select": "omostatusreason, count(*)", "$group": "omostatusreason"})
#                 response.raise_for_status()
#                 data = response.json()
#                 print(name, data)
#                 print()
#     asyncio.run(sample_test())

if __name__ == "__main__":
    test_state = HPDAgentState(bbl="2024260003")
    result = asyncio.run(fetch_enforcement(test_state))
    print(result)