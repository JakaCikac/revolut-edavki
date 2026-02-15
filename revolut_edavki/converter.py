"""Converter module for revolut-edavki."""

import xml.etree.ElementTree as ET
from datetime import datetime
from xml.dom import minidom

import pandas as pd

# Import defusedxml for safe parsing only
try:
    import defusedxml.ElementTree as DefusedET

    DEFUSEDXML_AVAILABLE = True
except ImportError:
    DEFUSEDXML_AVAILABLE = False
    import warnings

    warnings.warn(
        "defusedxml not available, using standard xml library for parsing. Install defusedxml for XXE protection."
    )


def get_exchange_rate(date, currency):
    """Get exchange rate from BSRate XML for any currency to EUR.
    Args:
        date: datetime object
        currency: str, e.g. 'USD', 'CHF', 'GBP'
    Returns:
        float: exchange rate or None if not found
    """
    if currency == "EUR":
        return 1.0

    try:
        # Parse the BSRate XML file safely
        if DEFUSEDXML_AVAILABLE:
            tree = DefusedET.parse("bsrate.xml")
        else:
            tree = ET.parse("bsrate.xml")  # nosec B314 - Fallback only, defusedxml preferred
        root = tree.getroot()

        # Convert date to the format used in BSRate (DD.MM.YYYY)
        date_str = date.strftime("%d.%m.%Y")

        # Find the exchange rate for the currency on the given date
        for d in root.findall(".//D"):
            if d.get("DT") == date_str:
                for rate in d.findall("Rate"):
                    if rate.get("CurCode") == currency:
                        return float(rate.get("MidRate").replace(",", "."))
        print(f"Warning: No exchange rate found for {currency} on {date_str}")
        return None
    except Exception as e:
        print(f"Error getting exchange rate: {str(e)}")
        return None


def clean_fx_rate(fx_rate):
    """Clean FX rate value that might have currency codes.
    Args:
        fx_rate: str/float/int FX rate value
    Returns:
        float: cleaned FX rate, defaults to 1.0 if invalid
    """
    if pd.isna(fx_rate):
        return 1.0

    try:
        if isinstance(fx_rate, (int, float)):
            rate = float(fx_rate)
        else:
            # Remove currency codes and symbols
            rate_str = str(fx_rate).strip()
            for currency_code in [
                "USD",
                "EUR",
                "GBP",
                "CHF",
                "JPY",
                "CAD",
                "AUD",
                "NZD",
                "SEK",
                "NOK",
                "DKK",
                "PLN",
                "CZK",
                "HUF",
                "RON",
                "BGN",
                "HRK",
                "RSD",
                "TRY",
                "RUB",
                "CNY",
                "INR",
                "BRL",
                "ZAR",
                "MXN",
                "SGD",
                "HKD",
                "KRW",
                "THB",
                "MYR",
                "IDR",
                "PHP",
                "VND",
            ]:
                rate_str = rate_str.replace(currency_code, "")
            rate = float(rate_str.replace("$", "").replace("€", "").replace("£", "").replace(",", "").strip())

        if rate <= 0:
            print(f"Warning: Invalid FX rate {fx_rate}, using 1.0")
            return 1.0
        return rate
    except (ValueError, TypeError):
        print(f"Warning: Invalid FX rate '{fx_rate}', using 1.0")
        return 1.0


def clean_amount(amount, fx_rate=1.0, return_details=False):
    """Clean and convert amount to EUR using provided FX rate.
    Args:
        amount: str/float/int amount
        fx_rate: float exchange rate to EUR (default 1.0 for EUR amounts)
        return_details: bool, if True returns tuple with details
    Returns:
        float or tuple: if return_details is True, returns (original_amount, eur_amount, exchange_rate)
                       otherwise returns just the eur_amount
    """
    if pd.isna(amount):
        return (0.0, 0.0, fx_rate) if return_details else 0.0

    try:
        # Convert to float first
        if isinstance(amount, (int, float)):
            value = float(amount)
        else:
            # Remove currency codes (USD, EUR, GBP, etc.), symbols, and commas
            amount_str = str(amount).strip()
            # Remove common currency codes
            for currency_code in [
                "USD",
                "EUR",
                "GBP",
                "CHF",
                "JPY",
                "CAD",
                "AUD",
                "NZD",
                "SEK",
                "NOK",
                "DKK",
                "PLN",
                "CZK",
                "HUF",
                "RON",
                "BGN",
                "HRK",
                "RSD",
                "TRY",
                "RUB",
                "CNY",
                "INR",
                "BRL",
                "ZAR",
                "MXN",
                "SGD",
                "HKD",
                "KRW",
                "THB",
                "MYR",
                "IDR",
                "PHP",
                "VND",
            ]:
                amount_str = amount_str.replace(currency_code, "")
            # Remove currency symbols and commas
            value = float(amount_str.replace("$", "").replace("€", "").replace("£", "").replace(",", "").strip())
    except (ValueError, TypeError):
        print(f"Warning: Invalid amount '{amount}', using 0.0")
        return (0.0, 0.0, fx_rate) if return_details else 0.0

    # Validate and clean FX rate
    fx_rate = clean_fx_rate(fx_rate)

    # Convert to EUR using provided FX rate
    # For non-EUR currencies, we need to divide by the FX rate
    # because FX rate is EUR/USD (or EUR/GBP, etc.)
    eur_value = value / fx_rate if fx_rate != 1.0 else value

    return (value, eur_value, fx_rate) if return_details else eur_value


def load_data():
    # Load transactions
    transactions = pd.read_csv("transactions.csv")
    transactions["Date"] = pd.to_datetime(transactions["Date"], format="mixed")

    # Clean monetary values
    transactions["Price per share"] = transactions["Price per share"].apply(clean_amount)
    transactions["Total Amount"] = transactions["Total Amount"].apply(clean_amount)

    # Load company info
    company_info = pd.read_excel("Company_info.xlsx")

    return transactions, company_info


def filter_transactions_by_year(transactions, year):
    return transactions[transactions["Date"].dt.year == year]


def create_debug_csv(data, filename):
    """Create a debug CSV file with the provided data."""
    df = pd.DataFrame(data)

    if len(df) > 0:
        # Convert datetime to YYYY-MM-DD format
        if "Date" in df.columns:
            df["Date"] = pd.to_datetime(df["Date"]).dt.strftime("%Y-%m-%d")

        # Sort by date if possible
        if "Date" in df.columns:
            df = df.sort_values("Date")

    # Save to CSV
    df.to_csv(filename, index=False)
    print(f"Debug file created: {filename}")


def create_kdvp_xml(transactions, year, tax_number, taxpayer_type="FO"):
    print(f"\nProcessing KDVP for year {year}")

    # List to store debug information
    debug_data = []

    # Handle empty DataFrame
    if len(transactions) == 0:
        print("Warning: No transactions provided")
        transactions = pd.DataFrame(
            columns=["Date", "Type", "Ticker", "Quantity", "Price per share", "Total Amount", "Currency", "FX Rate"]
        )

    # Ensure Date column is datetime
    try:
        transactions["Date"] = pd.to_datetime(transactions["Date"])
    except Exception as e:
        print(f"Warning: Error converting dates: {str(e)}")
        transactions["Date"] = pd.NaT

    # Create root element
    root = ET.Element("Envelope")
    root.set("xmlns", "http://edavki.durs.si/Documents/Schemas/Doh_KDVP_9.xsd")
    root.set("xmlns:edp", "http://edavki.durs.si/Documents/Schemas/EDP-Common-1.xsd")

    # Create header
    header = ET.SubElement(root, "edp:Header")
    taxpayer = ET.SubElement(header, "edp:taxpayer")
    ET.SubElement(taxpayer, "edp:taxNumber").text = tax_number
    ET.SubElement(taxpayer, "edp:taxpayerType").text = taxpayer_type
    workflow = ET.SubElement(header, "edp:Workflow")
    ET.SubElement(workflow, "edp:DocumentWorkflowID").text = "O"

    # Add empty AttachmentList and Signatures
    ET.SubElement(root, "edp:AttachmentList")
    ET.SubElement(root, "edp:Signatures")

    # Create body
    body = ET.SubElement(root, "body")
    ET.SubElement(body, "edp:bodyContent")
    doh_kdvp = ET.SubElement(body, "Doh_KDVP")

    # Add KDVP section
    kdvp = ET.SubElement(doh_kdvp, "KDVP")
    ET.SubElement(kdvp, "DocumentWorkflowID").text = "O"
    ET.SubElement(kdvp, "Year").text = str(year)
    ET.SubElement(kdvp, "PeriodStart").text = f"{year}-01-01"
    ET.SubElement(kdvp, "PeriodEnd").text = f"{year}-12-31"
    ET.SubElement(kdvp, "IsResident").text = "true"

    # Filter buy/sell transactions, excluding index funds
    stock_transactions = transactions[
        (transactions["Type"].str.contains("BUY|SELL", na=False)) & (~transactions["Ticker"].isin(["VWCE"]))
    ]

    # Get tickers with sells in target year
    sells_in_year = stock_transactions[
        (stock_transactions["Type"].str.contains("SELL", na=False)) & (stock_transactions["Date"].dt.year == year)
    ]
    tickers = sells_in_year["Ticker"].unique()

    # Add counts
    ET.SubElement(kdvp, "SecurityCount").text = str(len(tickers))
    ET.SubElement(kdvp, "SecurityShortCount").text = "0"
    ET.SubElement(kdvp, "SecurityWithContractCount").text = "0"
    ET.SubElement(kdvp, "SecurityWithContractShortCount").text = "0"
    ET.SubElement(kdvp, "ShareCount").text = "0"

    # Process each ticker that has sells in the target year
    for ticker in tickers:
        # Get all transactions for this ticker
        ticker_transactions = stock_transactions[stock_transactions["Ticker"] == ticker]
        # Filter out sells from other years
        ticker_transactions = ticker_transactions[
            (ticker_transactions["Type"].str.contains("BUY", na=False))
            | (
                (ticker_transactions["Type"].str.contains("SELL", na=False))
                & (ticker_transactions["Date"].dt.year == year)
            )
        ]

        # Create KDVPItem
        kdvp_item = ET.SubElement(doh_kdvp, "KDVPItem")
        ET.SubElement(kdvp_item, "InventoryListType").text = "PLVP"
        ET.SubElement(kdvp_item, "Name").text = ticker
        ET.SubElement(kdvp_item, "HasForeignTax").text = "false"
        ET.SubElement(kdvp_item, "HasLossTransfer").text = "false"
        ET.SubElement(kdvp_item, "ForeignTransfer").text = "false"
        ET.SubElement(kdvp_item, "TaxDecreaseConformance").text = "false"

        # Add Securities section
        securities = ET.SubElement(kdvp_item, "Securities")
        ET.SubElement(securities, "Code").text = ticker
        ET.SubElement(securities, "Name").text = ticker
        ET.SubElement(securities, "IsFond").text = "false"

        # Process transactions
        row_id = 0
        running_quantity = 0

        for _, tx in ticker_transactions.iterrows():
            row = ET.SubElement(securities, "Row")
            ET.SubElement(row, "ID").text = str(row_id)

            # Get currency and convert amounts
            currency = tx["Currency"]
            fx_rate = clean_fx_rate(tx["FX Rate"]) if currency != "EUR" else 1.0

            # Convert amount
            orig_price, eur_price, rate = clean_amount(tx["Price per share"], fx_rate=fx_rate, return_details=True)

            if "BUY" in tx["Type"]:
                purchase = ET.SubElement(row, "Purchase")
                ET.SubElement(purchase, "F1").text = tx["Date"].strftime("%Y-%m-%d")
                ET.SubElement(purchase, "F2").text = "B"
                ET.SubElement(purchase, "F3").text = f"{tx['Quantity']:.8f}"
                ET.SubElement(purchase, "F4").text = f"{eur_price:.8f}"
                ET.SubElement(purchase, "F5").text = "0.0000"
                running_quantity += tx["Quantity"]

                # Add to debug data
                debug_data.append(
                    {
                        "Date": tx["Date"],  # Keep as datetime for proper sorting
                        "Type": "BUY",
                        "Ticker": ticker,
                        "Quantity": f"{tx['Quantity']:.8f}",
                        "Original_Price": f"{orig_price:.8f}",
                        "Original_Currency": currency,
                        "Exchange_Rate": f"{rate:.4f}",
                        "EUR_Price": f"{eur_price:.8f}",
                        "Running_Quantity": f"{running_quantity:.8f}",
                    }
                )

            elif "SELL" in tx["Type"]:
                sale = ET.SubElement(row, "Sale")
                ET.SubElement(sale, "F6").text = tx["Date"].strftime("%Y-%m-%d")
                ET.SubElement(sale, "F7").text = f"{tx['Quantity']:.8f}"
                ET.SubElement(sale, "F9").text = f"{eur_price:.8f}"
                running_quantity -= tx["Quantity"]

                # Add to debug data
                debug_data.append(
                    {
                        "Date": tx["Date"],  # Keep as datetime for proper sorting
                        "Type": "SELL",
                        "Ticker": ticker,
                        "Quantity": f"{tx['Quantity']:.8f}",
                        "Original_Price": f"{orig_price:.8f}",
                        "Original_Currency": currency,
                        "Exchange_Rate": f"{rate:.4f}",
                        "EUR_Price": f"{eur_price:.8f}",
                        "Running_Quantity": f"{running_quantity:.8f}",
                    }
                )

            ET.SubElement(row, "F8").text = f"{running_quantity:.8f}"
            row_id += 1

    # Pretty print XML
    xmlstr = minidom.parseString(ET.tostring(root)).toprettyxml(
        indent="    "
    )  # nosec B318 - Parsing internally generated XML

    # Save XML file
    with open("Doh-KDVP.xml", "w", encoding="utf-8") as f:
        f.write(xmlstr)

    # Save debug CSV
    create_debug_csv(debug_data, "debug_kdvp.csv")


def create_div_xml(transactions, company_info, year, tax_number, taxpayer_type="FO"):
    print(f"\nProcessing dividends for year {year}")

    # List to store debug information
    debug_data = []

    # Handle empty DataFrame
    if len(transactions) == 0:
        print("Warning: No transactions provided")
        transactions = pd.DataFrame(
            columns=["Date", "Type", "Ticker", "Quantity", "Price per share", "Total Amount", "Currency", "FX Rate"]
        )

    # Handle empty company info
    if len(company_info) == 0:
        print("Warning: No company info provided")
        company_info = pd.DataFrame(columns=["Symbol", "Name", "Address", "CountryCode", "ISIN"])

    # Ensure Date column is datetime
    try:
        transactions["Date"] = pd.to_datetime(transactions["Date"])
    except Exception as e:
        print(f"Warning: Error converting dates: {str(e)}")
        transactions["Date"] = pd.NaT

    # Create root element
    root = ET.Element("Envelope")
    root.set("xmlns", "http://edavki.durs.si/Documents/Schemas/Doh_Div_3.xsd")
    root.set("xmlns:edp", "http://edavki.durs.si/Documents/Schemas/EDP-Common-1.xsd")

    # Create header
    header = ET.SubElement(root, "edp:Header")
    taxpayer = ET.SubElement(header, "edp:taxpayer")
    ET.SubElement(taxpayer, "edp:taxNumber").text = tax_number
    ET.SubElement(taxpayer, "edp:taxpayerType").text = taxpayer_type
    workflow = ET.SubElement(header, "edp:Workflow")
    ET.SubElement(workflow, "edp:DocumentWorkflowID").text = "O"

    # Add empty AttachmentList and Signatures
    ET.SubElement(root, "edp:AttachmentList")
    ET.SubElement(root, "edp:Signatures")

    # Create body
    body = ET.SubElement(root, "body")
    doh_div = ET.SubElement(body, "Doh_Div")
    ET.SubElement(doh_div, "Period").text = str(year)

    # Filter dividend transactions for the specific year
    dividend_transactions = transactions[
        (transactions["Type"] == "DIVIDEND")
        & (transactions["Date"].dt.year == year)
        & (~transactions["Ticker"].isin(["VWCE"]))  # Exclude index funds
    ]

    print(f"Found {len(dividend_transactions)} dividend transactions for {year}")

    # Process each dividend
    for _, tx in dividend_transactions.iterrows():
        print(f"\nProcessing dividend: {tx['Ticker']} on {tx['Date'].strftime('%Y-%m-%d')}")

        # Get company info
        company_matches = company_info[company_info["Symbol"] == tx["Ticker"]]
        if len(company_matches) == 0:
            print(f"Warning: No company info found for {tx['Ticker']}")
            continue

        company = company_matches.iloc[0]
        print(f"Found company info: {company['Name']} ({company['CountryCode']})")

        # Get currency and FX rate
        currency = tx["Currency"]
        fx_rate = clean_fx_rate(tx["FX Rate"]) if currency != "EUR" else 1.0

        # Convert amount
        orig_amount, eur_amount, rate = clean_amount(tx["Total Amount"], fx_rate=fx_rate, return_details=True)
        print(f"Amount: {eur_amount:.2f} EUR (original: {orig_amount:.2f} {currency}, rate: {rate})")

        # Add to debug data
        debug_data.append(
            {
                "Date": tx["Date"],  # Keep as datetime for proper sorting
                "Ticker": tx["Ticker"],
                "Company": company["Name"],
                "Country": company["CountryCode"],
                "Original_Amount": f"{abs(orig_amount):.2f}",
                "Original_Currency": currency,
                "Exchange_Rate": f"{rate:.4f}",
                "EUR_Amount": f"{abs(eur_amount):.2f}",
                "ISIN": company.get("ISIN", ""),
                "Address": company["Address"],
            }
        )

        # Create dividend item as direct child of body (per new schema)
        div_item = ET.SubElement(body, "Dividend")
        ET.SubElement(div_item, "Date").text = tx["Date"].strftime("%Y-%m-%d")
        ET.SubElement(div_item, "PayerIdentificationNumber").text = company.get("ISIN", "")
        ET.SubElement(div_item, "PayerName").text = company["Name"]
        ET.SubElement(div_item, "PayerAddress").text = company["Address"]
        ET.SubElement(div_item, "PayerCountry").text = company["CountryCode"]
        ET.SubElement(div_item, "Type").text = "1"  # Assuming all are type 1
        ET.SubElement(div_item, "Value").text = f"{abs(eur_amount):.2f}"
        ET.SubElement(div_item, "ForeignTax").text = "0.00"  # You might want to update this based on actual data
        ET.SubElement(div_item, "SourceCountry").text = company["CountryCode"]
        ET.SubElement(div_item, "ReliefStatement").text = ""

    # Pretty print XML
    xmlstr = minidom.parseString(ET.tostring(root)).toprettyxml(
        indent="    "
    )  # nosec B318 - Parsing internally generated XML

    # Save XML file
    with open("Doh-Div.xml", "w", encoding="utf-8") as f:
        f.write(xmlstr)

    # Save debug CSV
    create_debug_csv(debug_data, "debug_dividends.csv")


def create_ifi_xml(transactions, year, tax_number, taxpayer_type="FO"):
    print(f"\nProcessing IFI for year {year}")

    # List to store debug information
    debug_data = []

    # Handle empty DataFrame
    if len(transactions) == 0:
        print("Warning: No transactions provided")
        transactions = pd.DataFrame(
            columns=["Date", "Type", "Ticker", "Quantity", "Price per share", "Total Amount", "Currency", "FX Rate"]
        )

    # Ensure Date column is datetime
    try:
        transactions["Date"] = pd.to_datetime(transactions["Date"])
    except Exception as e:
        print(f"Warning: Error converting dates: {str(e)}")
        transactions["Date"] = pd.NaT

    # Create root element
    root = ET.Element("Envelope")
    root.set("xmlns", "http://edavki.durs.si/Documents/Schemas/D_IFI_4.xsd")
    root.set("xmlns:edp", "http://edavki.durs.si/Documents/Schemas/EDP-Common-1.xsd")

    # Create header
    header = ET.SubElement(root, "edp:Header")
    taxpayer = ET.SubElement(header, "edp:taxpayer")
    ET.SubElement(taxpayer, "edp:taxNumber").text = tax_number
    ET.SubElement(taxpayer, "edp:taxpayerType").text = taxpayer_type
    workflow = ET.SubElement(header, "edp:Workflow")
    ET.SubElement(workflow, "edp:DocumentWorkflowID").text = "O"

    # Add empty AttachmentList and Signatures
    ET.SubElement(root, "edp:AttachmentList")
    ET.SubElement(root, "edp:Signatures")

    # Create body
    body = ET.SubElement(root, "body")
    ET.SubElement(body, "edp:bodyContent")
    d_ifi = ET.SubElement(body, "D_IFI")

    # Add period
    ET.SubElement(d_ifi, "PeriodStart").text = f"{year}-01-01"
    ET.SubElement(d_ifi, "PeriodEnd").text = f"{year}-12-31"
    ET.SubElement(d_ifi, "TelephoneNumber").text = ""
    ET.SubElement(d_ifi, "Email").text = ""

    # Filter index fund transactions
    ifi_transactions = transactions[transactions["Ticker"] == "VWCE"]

    # Process each transaction
    for _, tx in ifi_transactions.iterrows():
        if "BUY" in tx["Type"] or "SELL" in tx["Type"]:
            # Get currency and FX rate
            currency = tx["Currency"]
            fx_rate = clean_fx_rate(tx["FX Rate"]) if currency != "EUR" else 1.0

            # Convert amount
            orig_amount, eur_amount, rate = clean_amount(tx["Total Amount"], fx_rate=fx_rate, return_details=True)

            # Add to debug data
            debug_data.append(
                {
                    "Date": tx["Date"],  # Keep as datetime for proper sorting
                    "Type": "BUY" if "BUY" in tx["Type"] else "SELL",
                    "Original_Amount": f"{abs(orig_amount):.2f}",
                    "Original_Currency": currency,
                    "Exchange_Rate": f"{rate:.4f}",
                    "EUR_Amount": f"{abs(eur_amount):.2f}",
                    "Quantity": tx["Quantity"],
                }
            )

            # Create XML item
            item = ET.SubElement(d_ifi, "Item")
            ET.SubElement(item, "Name").text = "VWCE"
            ET.SubElement(item, "Code").text = "VWCE"
            ET.SubElement(item, "IsFond").text = "true"
            ET.SubElement(item, "Date").text = tx["Date"].strftime("%Y-%m-%d")
            ET.SubElement(item, "Value").text = f"{abs(eur_amount):.2f}"
            ET.SubElement(item, "Type").text = "B" if "BUY" in tx["Type"] else "S"

    # Pretty print XML
    xmlstr = minidom.parseString(ET.tostring(root)).toprettyxml(
        indent="    "
    )  # nosec B318 - Parsing internally generated XML

    # Save XML file
    with open("D-IFI.xml", "w", encoding="utf-8") as f:
        f.write(xmlstr)

    # Save debug CSV
    create_debug_csv(debug_data, "debug_ifi.csv")
