"""Web application for revolut-edavki."""

import os
from flask import Flask, render_template, request, send_file, jsonify
import pandas as pd
import requests
from datetime import datetime

from . import converter  # our existing converter module
from . import utils  # our utilities module

app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = os.getenv("UPLOAD_PATH", "uploads")
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16MB max file size
app.config["DEBUG"] = os.getenv("DEBUG", "false").lower() == "true"

# Ensure upload directory exists
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in {
        "csv",
        "xlsx",
        "xml",
    }


def get_bsrate():
    url = "https://www.bsi.si/_data/tecajnice/dtecbs-l.xml"
    response = requests.get(url)
    if response.status_code == 200:
        # Save the file
        with open(os.path.join(app.config["UPLOAD_FOLDER"], "bsrate.xml"), "wb") as f:
            f.write(response.content)
        return True
    return False


def process_files(
    transactions_file, company_info_file, year, tax_number, taxpayer_type="FO"
):
    try:
        # Hash taxpayer info
        hashed_tax_id = utils.hash_taxpayer_id(tax_number)

        # Create taxpayer-specific upload folder
        taxpayer_folder = os.path.join(app.config["UPLOAD_FOLDER"], hashed_tax_id)
        os.makedirs(taxpayer_folder, exist_ok=True)

        # Update BSRate in the background
        get_bsrate()

        # Hash filenames and save files
        transactions_filename = utils.hash_filename(transactions_file.filename)
        company_info_filename = utils.hash_filename(company_info_file.filename)

        transactions_path = os.path.join(taxpayer_folder, transactions_filename)
        company_info_path = os.path.join(taxpayer_folder, company_info_filename)

        transactions_file.save(transactions_path)
        company_info_file.save(company_info_path)

        # Load data
        transactions = pd.read_csv(transactions_path)
        print(f"Loaded transactions: {len(transactions)} rows")

        transactions["Date"] = pd.to_datetime(transactions["Date"], format="mixed")
        print("Dates parsed successfully")

        company_info = pd.read_excel(company_info_path)
        print(f"Loaded company info: {len(company_info)} rows")

        # Validate company info columns
        required_columns = ["Symbol", "Name", "Address", "CountryCode", "ISIN"]
        missing_columns = [
            col for col in required_columns if col not in company_info.columns
        ]

        if missing_columns:
            raise ValueError(
                f"Missing required columns in Company Info file: {', '.join(missing_columns)}"
            )

        # Filter transactions for the selected year
        transactions_year = transactions[transactions["Date"].dt.year == year]
        print(f"Filtered transactions for {year}: {len(transactions_year)} rows")

        # Generate preview data
        preview = {"kdvp": [], "dividends": [], "ifi": []}

        # KDVP preview - only stocks with sells in target year
        stock_tx = transactions_year[
            (transactions_year["Type"].str.contains("BUY|SELL", na=False))
            & (~transactions_year["Ticker"].isin(["VWCE"]))
        ]
        print(f"Found {len(stock_tx)} stock transactions")

        # Get tickers with sells in target year
        sell_tickers = stock_tx[stock_tx["Type"].str.contains("SELL", na=False)][
            "Ticker"
        ].unique()
        print(
            f"Found {len(sell_tickers)} tickers with sells: {', '.join(sell_tickers)}"
        )

        for ticker in sell_tickers:
            ticker_tx = transactions[transactions["Ticker"] == ticker]
            buys = ticker_tx[ticker_tx["Type"].str.contains("BUY", na=False)]
            sells = ticker_tx[
                (ticker_tx["Type"].str.contains("SELL", na=False))
                & (ticker_tx["Date"].dt.year == year)
            ]

            if len(sells) > 0:
                preview["kdvp"].append(
                    {
                        "ticker": ticker,
                        "buys": len(buys),
                        "sells": len(sells),
                        "last_buy": (
                            buys["Date"].max().strftime("%Y-%m-%d")
                            if len(buys) > 0
                            else "N/A"
                        ),
                        "last_sell": sells["Date"].max().strftime("%Y-%m-%d"),
                    }
                )

        # Dividends preview
        div_tx = transactions_year[
            (transactions_year["Type"] == "DIVIDEND")
            & (~transactions_year["Ticker"].isin(["VWCE"]))
        ]
        print(f"Found {len(div_tx)} dividend transactions")

        for _, tx in div_tx.iterrows():
            company_matches = company_info[company_info["Symbol"] == tx["Ticker"]]
            if len(company_matches) > 0:
                company = company_matches.iloc[0]
                amount = abs(
                    float(
                        str(tx["Total Amount"])
                        .replace("$", "")
                        .replace("€", "")
                        .replace(",", "")
                    )
                )
                preview["dividends"].append(
                    {
                        "date": tx["Date"].strftime("%Y-%m-%d"),
                        "ticker": tx["Ticker"],
                        "company": company["Name"],
                        "amount": amount,
                        "fx_rate": tx["FX Rate"],
                    }
                )
                print(
                    f"Added dividend: {tx['Ticker']} - {amount} ({tx['Date'].strftime('%Y-%m-%d')})"
                )

        # IFI preview
        ifi_tx = transactions_year[transactions_year["Ticker"] == "VWCE"]
        print(f"Found {len(ifi_tx)} IFI transactions")

        for _, tx in ifi_tx.iterrows():
            if "BUY" in tx["Type"] or "SELL" in tx["Type"]:
                amount = abs(
                    float(str(tx["Total Amount"]).replace("€", "").replace(",", ""))
                )
                preview["ifi"].append(
                    {
                        "date": tx["Date"].strftime("%Y-%m-%d"),
                        "type": "Buy" if "BUY" in tx["Type"] else "Sell",
                        "amount": amount,
                        "shares": tx["Quantity"],
                    }
                )
                print(
                    f"Added IFI transaction: {tx['Type']} - {amount} EUR ({tx['Date'].strftime('%Y-%m-%d')})"
                )

        print("\nGenerating XML files...")
        converter.create_kdvp_xml(transactions, year, tax_number, taxpayer_type)
        print("KDVP XML generated")
        converter.create_div_xml(
            transactions_year, company_info, year, tax_number, taxpayer_type
        )
        print("Dividend XML generated")
        converter.create_ifi_xml(transactions_year, year, tax_number, taxpayer_type)
        print("IFI XML generated")

        return preview
    except Exception as e:
        print(f"Error processing files: {str(e)}")
        raise


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/upload", methods=["POST"])
def upload():
    if "transactions" not in request.files or "company_info" not in request.files:
        return jsonify({"error": "Missing required files"}), 400

    transactions_file = request.files["transactions"]
    company_info_file = request.files["company_info"]
    year = int(request.form.get("year", datetime.now().year))
    tax_number = request.form.get("tax_number")
    taxpayer_type = request.form.get("taxpayer_type", "FO")

    if not all(
        allowed_file(f.filename) for f in [transactions_file, company_info_file]
    ):
        return jsonify({"error": "Invalid file type"}), 400

    preview = process_files(
        transactions_file, company_info_file, year, tax_number, taxpayer_type
    )
    return jsonify(preview)


@app.route("/download/<filename>")
def download(filename):
    allowed_files = [
        "Doh-KDVP.xml",
        "Doh-Div.xml",
        "D-IFI.xml",
        "debug_dividends.csv",
        "debug_kdvp.csv",
        "debug_ifi.csv",
    ]
    if filename not in allowed_files:
        return "File not found", 404
    return send_file(filename, as_attachment=True)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=59855)
