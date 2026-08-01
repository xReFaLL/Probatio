"""
Univers de titres de départ pour Probatio — listes statiques embarquées dans
le repo (voir brief projet, section "Univers de titres de départ").

Ces listes sont figées à une date donnée (composition S&P 500 / CAC 40) et
devront être mises à jour périodiquement (rebalancements trimestriels). Elles
sont volontairement statiques pour le MVP — pas d'appel réseau pour les
récupérer dynamiquement, conformément au principe "aucune API en direct".

Format des tickers : convention yfinance (ex: classes d'actions séparées par
un tiret : BRK-B, BF-B ; suffixe .PA pour Euronext Paris).
"""

# ---------------------------------------------------------------------------
# S&P 500 — (ticker yfinance, nom)
# Composition figée à titre indicatif (~503 lignes, 2 classes d'actions pour
# Alphabet, Fox Corporation, News Corp). Source : Wikipedia "List of S&P 500
# companies", à recouper/actualiser périodiquement.
# ---------------------------------------------------------------------------
SP500 = [
    ("MMM", "3M"), ("AOS", "A. O. Smith"), ("ABT", "Abbott Laboratories"),
    ("ABBV", "AbbVie"), ("ACN", "Accenture"), ("ADBE", "Adobe Inc."),
    ("AMD", "Advanced Micro Devices"), ("AES", "AES Corporation"), ("AFL", "Aflac"),
    ("A", "Agilent Technologies"), ("APD", "Air Products"), ("ABNB", "Airbnb"),
    ("AKAM", "Akamai Technologies"), ("ALB", "Albemarle Corporation"),
    ("ARE", "Alexandria Real Estate Equities"), ("ALGN", "Align Technology"),
    ("ALLE", "Allegion"), ("LNT", "Alliant Energy"), ("ALL", "Allstate"),
    ("GOOGL", "Alphabet Inc. (Class A)"), ("GOOG", "Alphabet Inc. (Class C)"),
    ("MO", "Altria"), ("AMZN", "Amazon"), ("AMCR", "Amcor"), ("AEE", "Ameren"),
    ("AEP", "American Electric Power"), ("AXP", "American Express"),
    ("AIG", "American International Group"), ("AMT", "American Tower"),
    ("AWK", "American Water Works"), ("AMP", "Ameriprise Financial"),
    ("AME", "Ametek"), ("AMGN", "Amgen"), ("APH", "Amphenol"),
    ("ADI", "Analog Devices"), ("AON", "Aon plc"), ("APA", "APA Corporation"),
    ("APO", "Apollo Global Management"), ("AAPL", "Apple Inc."),
    ("AMAT", "Applied Materials"), ("APP", "AppLovin"), ("APTV", "Aptiv"),
    ("ACGL", "Arch Capital Group"), ("ADM", "Archer Daniels Midland"),
    ("ARES", "Ares Management"), ("ANET", "Arista Networks"),
    ("AJG", "Arthur J. Gallagher & Co."), ("AIZ", "Assurant"), ("T", "AT&T"),
    ("ATO", "Atmos Energy"), ("ADSK", "Autodesk"),
    ("ADP", "Automatic Data Processing"), ("AZO", "AutoZone"),
    ("AVB", "AvalonBay Communities"), ("AVY", "Avery Dennison"),
    ("AXON", "Axon Enterprise"), ("BKR", "Baker Hughes"), ("BALL", "Ball Corporation"),
    ("BAC", "Bank of America"), ("BAX", "Baxter International"),
    ("BDX", "Becton Dickinson"), ("BRK-B", "Berkshire Hathaway"), ("BBY", "Best Buy"),
    ("TECH", "Bio-Techne"), ("BIIB", "Biogen"), ("BLK", "BlackRock"),
    ("BX", "Blackstone Inc."), ("XYZ", "Block, Inc."), ("BNY", "BNY Mellon"),
    ("BA", "Boeing"), ("BKNG", "Booking Holdings"), ("BSX", "Boston Scientific"),
    ("BMY", "Bristol Myers Squibb"), ("AVGO", "Broadcom"),
    ("BR", "Broadridge Financial Solutions"), ("BRO", "Brown & Brown"),
    ("BF-B", "Brown-Forman"), ("BLDR", "Builders FirstSource"),
    ("BG", "Bunge Global"), ("BXP", "BXP, Inc."), ("CHRW", "C.H. Robinson"),
    ("CDNS", "Cadence Design Systems"), ("CPT", "Camden Property Trust"),
    ("CPB", "Campbell's Company (The)"), ("COF", "Capital One"),
    ("CAH", "Cardinal Health"), ("CCL", "Carnival Corporation"),
    ("CARR", "Carrier Global"), ("CVNA", "Carvana"), ("CASY", "Casey's"),
    ("CAT", "Caterpillar Inc."), ("CBOE", "Cboe Global Markets"),
    ("CBRE", "CBRE Group"), ("CDW", "CDW Corporation"), ("COR", "Cencora"),
    ("CNC", "Centene Corporation"), ("CNP", "CenterPoint Energy"),
    ("CF", "CF Industries"), ("CRL", "Charles River Laboratories"),
    ("SCHW", "Charles Schwab Corporation"), ("CHTR", "Charter Communications"),
    ("CVX", "Chevron Corporation"), ("CMG", "Chipotle Mexican Grill"),
    ("CB", "Chubb Limited"), ("CHD", "Church & Dwight"), ("CIEN", "Ciena"),
    ("CI", "Cigna"), ("CINF", "Cincinnati Financial"), ("CTAS", "Cintas"),
    ("CSCO", "Cisco"), ("C", "Citigroup"), ("CFG", "Citizens Financial Group"),
    ("CLX", "Clorox"), ("CME", "CME Group"), ("CMS", "CMS Energy"),
    ("KO", "Coca-Cola Company (The)"), ("CTSH", "Cognizant"),
    ("COHR", "Coherent Corp."), ("COIN", "Coinbase"), ("CL", "Colgate-Palmolive"),
    ("CMCSA", "Comcast"), ("FIX", "Comfort Systems USA"), ("CAG", "Conagra Brands"),
    ("COP", "ConocoPhillips"), ("ED", "Consolidated Edison"),
    ("STZ", "Constellation Brands"), ("CEG", "Constellation Energy"),
    ("COO", "Cooper Companies (The)"), ("CPRT", "Copart"), ("GLW", "Corning Inc."),
    ("CPAY", "Corpay"), ("CTVA", "Corteva"), ("CSGP", "CoStar Group"),
    ("COST", "Costco"), ("CRH", "CRH plc"), ("CRWD", "CrowdStrike"),
    ("CCI", "Crown Castle"), ("CSX", "CSX Corporation"), ("CMI", "Cummins"),
    ("CVS", "CVS Health"), ("DHR", "Danaher Corporation"),
    ("DRI", "Darden Restaurants"), ("DDOG", "Datadog"), ("DVA", "DaVita"),
    ("DECK", "Deckers Brands"), ("DE", "Deere & Company"),
    ("DELL", "Dell Technologies"), ("DAL", "Delta Air Lines"),
    ("DVN", "Devon Energy"), ("DXCM", "Dexcom"), ("FANG", "Diamondback Energy"),
    ("DLR", "Digital Realty"), ("DG", "Dollar General"), ("DLTR", "Dollar Tree"),
    ("D", "Dominion Energy"), ("DPZ", "Domino's"), ("DASH", "DoorDash"),
    ("DOV", "Dover Corporation"), ("DOW", "Dow Inc."), ("DHI", "D. R. Horton"),
    ("DTE", "DTE Energy"), ("DUK", "Duke Energy"), ("DD", "DuPont"),
    ("ETN", "Eaton Corporation"), ("EBAY", "eBay Inc."), ("SATS", "EchoStar"),
    ("ECL", "Ecolab"), ("EIX", "Edison International"),
    ("EW", "Edwards Lifesciences"), ("EA", "Electronic Arts"),
    ("ELV", "Elevance Health"), ("EME", "Emcor"), ("EMR", "Emerson Electric"),
    ("ETR", "Entergy"), ("EOG", "EOG Resources"), ("EPAM", "EPAM Systems"),
    ("EQT", "EQT Corporation"), ("EFX", "Equifax"), ("EQIX", "Equinix"),
    ("EQR", "Equity Residential"), ("ERIE", "Erie Indemnity"),
    ("ESS", "Essex Property Trust"), ("EL", "Estée Lauder Companies (The)"),
    ("EG", "Everest Group"), ("EVRG", "Evergy"), ("ES", "Eversource Energy"),
    ("EXC", "Exelon"), ("EXE", "Expand Energy"), ("EXPE", "Expedia Group"),
    ("EXPD", "Expeditors International"), ("EXR", "Extra Space Storage"),
    ("XOM", "ExxonMobil"), ("FFIV", "F5, Inc."), ("FDS", "FactSet"),
    ("FICO", "Fair Isaac"), ("FAST", "Fastenal"),
    ("FRT", "Federal Realty Investment Trust"), ("FDX", "FedEx"),
    ("FIS", "Fidelity National Information Services"),
    ("FITB", "Fifth Third Bancorp"), ("FSLR", "First Solar"),
    ("FE", "FirstEnergy"), ("FISV", "Fiserv"), ("F", "Ford Motor Company"),
    ("FTNT", "Fortinet"), ("FTV", "Fortive"), ("FOXA", "Fox Corporation (Class A)"),
    ("FOX", "Fox Corporation (Class B)"), ("BEN", "Franklin Resources"),
    ("FCX", "Freeport-McMoRan"), ("GRMN", "Garmin"), ("IT", "Gartner"),
    ("GE", "GE Aerospace"), ("GEHC", "GE HealthCare"), ("GEV", "GE Vernova"),
    ("GEN", "Gen Digital"), ("GNRC", "Generac"), ("GD", "General Dynamics"),
    ("GIS", "General Mills"), ("GM", "General Motors"),
    ("GPC", "Genuine Parts Company"), ("GILD", "Gilead Sciences"),
    ("GPN", "Global Payments"), ("GL", "Globe Life"), ("GDDY", "GoDaddy"),
    ("GS", "Goldman Sachs"), ("HAL", "Halliburton"), ("HIG", "Hartford (The)"),
    ("HAS", "Hasbro"), ("HCA", "HCA Healthcare"), ("DOC", "Healthpeak Properties"),
    ("HSIC", "Henry Schein"), ("HSY", "Hershey Company (The)"),
    ("HPE", "Hewlett Packard Enterprise"), ("HLT", "Hilton Worldwide"),
    ("HD", "Home Depot (The)"), ("HON", "Honeywell"), ("HRL", "Hormel Foods"),
    ("HST", "Host Hotels & Resorts"), ("HWM", "Howmet Aerospace"),
    ("HPQ", "HP Inc."), ("HUBB", "Hubbell Incorporated"), ("HUM", "Humana"),
    ("HBAN", "Huntington Bancshares"), ("HII", "Huntington Ingalls Industries"),
    ("IBM", "IBM"), ("IEX", "IDEX Corporation"), ("IDXX", "Idexx Laboratories"),
    ("ITW", "Illinois Tool Works"), ("INCY", "Incyte"), ("IR", "Ingersoll Rand"),
    ("PODD", "Insulet Corporation"), ("INTC", "Intel"),
    ("IBKR", "Interactive Brokers"), ("ICE", "Intercontinental Exchange"),
    ("IFF", "International Flavors & Fragrances"), ("IP", "International Paper"),
    ("INTU", "Intuit"), ("ISRG", "Intuitive Surgical"), ("IVZ", "Invesco"),
    ("INVH", "Invitation Homes"), ("IQV", "IQVIA"), ("IRM", "Iron Mountain"),
    ("JBHT", "J.B. Hunt"), ("JBL", "Jabil"), ("JKHY", "Jack Henry & Associates"),
    ("J", "Jacobs Solutions"), ("JNJ", "Johnson & Johnson"),
    ("JCI", "Johnson Controls"), ("JPM", "JPMorgan Chase"), ("KVUE", "Kenvue"),
    ("KDP", "Keurig Dr Pepper"), ("KEY", "KeyCorp"),
    ("KEYS", "Keysight Technologies"), ("KMB", "Kimberly-Clark"),
    ("KIM", "Kimco Realty"), ("KMI", "Kinder Morgan"), ("KKR", "KKR & Co."),
    ("KLAC", "KLA Corporation"), ("KHC", "Kraft Heinz"), ("KR", "Kroger"),
    ("LHX", "L3Harris"), ("LH", "Labcorp"), ("LRCX", "Lam Research"),
    ("LVS", "Las Vegas Sands"), ("LDOS", "Leidos"), ("LEN", "Lennar"),
    ("LII", "Lennox International"), ("LLY", "Lilly (Eli)"), ("LIN", "Linde plc"),
    ("LYV", "Live Nation Entertainment"), ("LMT", "Lockheed Martin"),
    ("L", "Loews Corporation"), ("LOW", "Lowe's"), ("LULU", "Lululemon Athletica"),
    ("LITE", "Lumentum"), ("LYB", "LyondellBasell"), ("MTB", "M&T Bank"),
    ("MPC", "Marathon Petroleum"), ("MAR", "Marriott International"),
    ("MMC", "Marsh McLennan"), ("MLM", "Martin Marietta Materials"),
    ("MAS", "Masco"), ("MA", "Mastercard"), ("MKC", "McCormick & Company"),
    ("MCD", "McDonald's"), ("MCK", "McKesson Corporation"), ("MDT", "Medtronic"),
    ("MRK", "Merck & Co."), ("META", "Meta Platforms"), ("MET", "MetLife"),
    ("MTD", "Mettler Toledo"), ("MGM", "MGM Resorts"),
    ("MCHP", "Microchip Technology"), ("MU", "Micron Technology"),
    ("MSFT", "Microsoft"), ("MAA", "Mid-America Apartment Communities"),
    ("MRNA", "Moderna"), ("TAP", "Molson Coors Beverage Company"),
    ("MDLZ", "Mondelez International"), ("MPWR", "Monolithic Power Systems"),
    ("MNST", "Monster Beverage"), ("MCO", "Moody's Corporation"),
    ("MS", "Morgan Stanley"), ("MOS", "Mosaic Company (The)"),
    ("MSI", "Motorola Solutions"), ("MSCI", "MSCI Inc."), ("NDAQ", "Nasdaq, Inc."),
    ("NTAP", "NetApp"), ("NFLX", "Netflix"), ("NEM", "Newmont"),
    ("NWSA", "News Corp (Class A)"), ("NWS", "News Corp (Class B)"),
    ("NEE", "NextEra Energy"), ("NKE", "Nike, Inc."), ("NI", "NiSource"),
    ("NDSN", "Nordson Corporation"), ("NSC", "Norfolk Southern"),
    ("NTRS", "Northern Trust"), ("NOC", "Northrop Grumman"),
    ("NCLH", "Norwegian Cruise Line Holdings"), ("NRG", "NRG Energy"),
    ("NUE", "Nucor"), ("NVDA", "Nvidia"), ("NVR", "NVR, Inc."),
    ("NXPI", "NXP Semiconductors"), ("ORLY", "O'Reilly Automotive"),
    ("OXY", "Occidental Petroleum"), ("ODFL", "Old Dominion"),
    ("OMC", "Omnicom Group"), ("ON", "ON Semiconductor"), ("OKE", "Oneok"),
    ("ORCL", "Oracle Corporation"), ("OTIS", "Otis Worldwide"), ("PCAR", "Paccar"),
    ("PKG", "Packaging Corporation of America"), ("PLTR", "Palantir Technologies"),
    ("PANW", "Palo Alto Networks"), ("PSKY", "Paramount Skydance Corporation"),
    ("PH", "Parker Hannifin"), ("PAYX", "Paychex"), ("PYPL", "PayPal"),
    ("PNR", "Pentair"), ("PEP", "PepsiCo"), ("PFE", "Pfizer"),
    ("PCG", "PG&E Corporation"), ("PM", "Philip Morris International"),
    ("PSX", "Phillips 66"), ("PNW", "Pinnacle West Capital"),
    ("PNC", "PNC Financial Services"), ("POOL", "Pool Corporation"),
    ("PPG", "PPG Industries"), ("PPL", "PPL Corporation"),
    ("PFG", "Principal Financial Group"), ("PG", "Procter & Gamble"),
    ("PGR", "Progressive Corporation"), ("PLD", "Prologis"),
    ("PRU", "Prudential Financial"), ("PEG", "Public Service Enterprise Group"),
    ("PTC", "PTC Inc."), ("PSA", "Public Storage"), ("PHM", "PulteGroup"),
    ("PWR", "Quanta Services"), ("QCOM", "Qualcomm"), ("DGX", "Quest Diagnostics"),
    ("Q", "Qnity Electronics"), ("RL", "Ralph Lauren Corporation"),
    ("RJF", "Raymond James Financial"), ("RTX", "RTX Corporation"),
    ("O", "Realty Income"), ("REG", "Regency Centers"),
    ("REGN", "Regeneron Pharmaceuticals"), ("RF", "Regions Financial Corporation"),
    ("RSG", "Republic Services"), ("RMD", "ResMed"), ("RVTY", "Revvity"),
    ("HOOD", "Robinhood Markets"), ("ROK", "Rockwell Automation"),
    ("ROL", "Rollins, Inc."), ("ROP", "Roper Technologies"),
    ("ROST", "Ross Stores"), ("RCL", "Royal Caribbean Group"),
    ("SPGI", "S&P Global"), ("CRM", "Salesforce"), ("SNDK", "Sandisk"),
    ("SBAC", "SBA Communications"), ("SLB", "Schlumberger"),
    ("STX", "Seagate Technology"), ("SRE", "Sempra"), ("NOW", "ServiceNow"),
    ("SHW", "Sherwin-Williams"), ("SPG", "Simon Property Group"),
    ("SWKS", "Skyworks Solutions"), ("SJM", "J.M. Smucker Company (The)"),
    ("SW", "Smurfit Westrock"), ("SNA", "Snap-on"), ("SOLV", "Solventum"),
    ("SO", "Southern Company"), ("LUV", "Southwest Airlines"),
    ("SWK", "Stanley Black & Decker"), ("SBUX", "Starbucks"),
    ("STT", "State Street Corporation"), ("STLD", "Steel Dynamics"),
    ("STE", "Steris"), ("SYK", "Stryker Corporation"), ("SMCI", "Supermicro"),
    ("SYF", "Synchrony Financial"), ("SNPS", "Synopsys"), ("SYY", "Sysco"),
    ("TMUS", "T-Mobile US"), ("TROW", "T. Rowe Price"),
    ("TTWO", "Take-Two Interactive"), ("TPR", "Tapestry, Inc."),
    ("TRGP", "Targa Resources"), ("TGT", "Target Corporation"),
    ("TEL", "TE Connectivity"), ("TDY", "Teledyne Technologies"),
    ("TER", "Teradyne"), ("TSLA", "Tesla, Inc."), ("TXN", "Texas Instruments"),
    ("TPL", "Texas Pacific Land Corporation"), ("TXT", "Textron"),
    ("TMO", "Thermo Fisher Scientific"), ("TJX", "TJX Companies"),
    ("TKO", "TKO Group Holdings"), ("TTD", "Trade Desk (The)"),
    ("TSCO", "Tractor Supply"), ("TT", "Trane Technologies"),
    ("TDG", "TransDigm Group"), ("TRV", "Travelers Companies (The)"),
    ("TRMB", "Trimble Inc."), ("TFC", "Truist Financial"),
    ("TYL", "Tyler Technologies"), ("TSN", "Tyson Foods"), ("USB", "U.S. Bancorp"),
    ("UBER", "Uber"), ("UDR", "UDR, Inc."), ("ULTA", "Ulta Beauty"),
    ("UNP", "Union Pacific Corporation"), ("UAL", "United Airlines Holdings"),
    ("UPS", "United Parcel Service"), ("URI", "United Rentals"),
    ("UNH", "UnitedHealth Group"), ("UHS", "Universal Health Services"),
    ("VLO", "Valero Energy"), ("VEEV", "Veeva Systems"), ("VTR", "Ventas"),
    ("VLTO", "Veralto"), ("VRSN", "Verisign"), ("VRSK", "Verisk Analytics"),
    ("VZ", "Verizon"), ("VRTX", "Vertex Pharmaceuticals"), ("VRT", "Vertiv"),
    ("VTRS", "Viatris"), ("VICI", "Vici Properties"), ("V", "Visa Inc."),
    ("VST", "Vistra Corp."), ("VMC", "Vulcan Materials Company"),
    ("WRB", "W. R. Berkley Corporation"), ("GWW", "W. W. Grainger"),
    ("WAB", "Wabtec"), ("WMT", "Walmart"), ("DIS", "Walt Disney Company (The)"),
    ("WBD", "Warner Bros. Discovery"), ("WM", "Waste Management"),
    ("WAT", "Waters Corporation"), ("WEC", "WEC Energy Group"),
    ("WFC", "Wells Fargo"), ("WELL", "Welltower"),
    ("WST", "West Pharmaceutical Services"), ("WDC", "Western Digital"),
    ("WY", "Weyerhaeuser"), ("WSM", "Williams-Sonoma, Inc."),
    ("WMB", "Williams Companies"), ("WTW", "Willis Towers Watson"),
    ("WDAY", "Workday, Inc."), ("WYNN", "Wynn Resorts"), ("XEL", "Xcel Energy"),
    ("XYL", "Xylem Inc."), ("YUM", "Yum! Brands"), ("ZBRA", "Zebra Technologies"),
    ("ZBH", "Zimmer Biomet"), ("ZTS", "Zoetis"),
]

# ---------------------------------------------------------------------------
# CAC 40 — (ticker yfinance, nom). Composition figée à titre indicatif,
# révisée trimestriellement par le Conseil scientifique des indices Euronext.
# ---------------------------------------------------------------------------
CAC40 = [
    ("AI.PA", "Air Liquide"), ("AIR.PA", "Airbus"), ("MT.PA", "ArcelorMittal"),
    ("CS.PA", "Axa"), ("BNP.PA", "BNP Paribas"), ("EN.PA", "Bouygues"),
    ("CAP.PA", "Capgemini"), ("CA.PA", "Carrefour"), ("ACA.PA", "Crédit Agricole"),
    ("BN.PA", "Danone"), ("DSY.PA", "Dassault Systèmes"), ("EDEN.PA", "Edenred"),
    ("ENGI.PA", "Engie"), ("EL.PA", "EssilorLuxottica"),
    ("ERF.PA", "Eurofins Scientific"), ("RMS.PA", "Hermès"), ("KER.PA", "Kering"),
    ("LR.PA", "Legrand"), ("OR.PA", "L'Oréal"), ("MC.PA", "LVMH"),
    ("ML.PA", "Michelin"), ("ORA.PA", "Orange"), ("RI.PA", "Pernod Ricard"),
    ("PUB.PA", "Publicis"), ("RNO.PA", "Renault"), ("SAF.PA", "Safran"),
    ("SGO.PA", "Saint-Gobain"), ("SAN.PA", "Sanofi"),
    ("SU.PA", "Schneider Electric"), ("GLE.PA", "Société Générale"),
    ("STMPA.PA", "STMicroelectronics"), ("STLAP.PA", "Stellantis"),
    ("TEP.PA", "Teleperformance"), ("HO.PA", "Thales"), ("TTE.PA", "TotalEnergies"),
    ("URW.PA", "Unibail-Rodamco-Westfield"), ("VIE.PA", "Veolia"),
    ("DG.PA", "Vinci"), ("WLN.PA", "Worldline"), ("ALO.PA", "Alstom"),
]

# ---------------------------------------------------------------------------
# Crypto — top 20-30 paires USDT sur Binance (tickers format Binance)
# ---------------------------------------------------------------------------
CRYPTO_PAIRS = [
    "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT", "ADAUSDT",
    "DOGEUSDT", "AVAXUSDT", "DOTUSDT", "TRXUSDT", "LINKUSDT", "MATICUSDT",
    "TONUSDT", "SHIBUSDT", "LTCUSDT", "BCHUSDT", "UNIUSDT", "ATOMUSDT",
    "XLMUSDT", "ETCUSDT", "NEARUSDT", "FILUSDT", "APTUSDT", "ARBUSDT",
    "OPUSDT", "SUIUSDT", "INJUSDT", "TIAUSDT",
]

# ---------------------------------------------------------------------------
# Forex — 6 paires majeures (tickers yfinance, suffixe =X)
# ---------------------------------------------------------------------------
FOREX_PAIRS = [
    ("EURUSD=X", "EUR/USD"), ("GBPUSD=X", "GBP/USD"), ("USDJPY=X", "USD/JPY"),
    ("USDCHF=X", "USD/CHF"), ("AUDUSD=X", "AUD/USD"), ("USDCAD=X", "USD/CAD"),
]

# ---------------------------------------------------------------------------
# Commodities — Or, Pétrole WTI, Argent (tickers futures Yahoo)
# ---------------------------------------------------------------------------
COMMODITIES = [
    ("GC=F", "Or (Gold Futures)"), ("CL=F", "Pétrole WTI (Crude Oil Futures)"),
    ("SI=F", "Argent (Silver Futures)"),
]

# ---------------------------------------------------------------------------
# Indices
# ---------------------------------------------------------------------------
INDICES = [
    ("^GSPC", "S&P 500"), ("^IXIC", "Nasdaq Composite"), ("^FCHI", "CAC 40"),
]

# ---------------------------------------------------------------------------
# Macro — séries FRED (Sprint 3). Univers non spécifié dans le brief projet ;
# sélection par défaut couvrant taux/inflation/PIB (mentionnés dans le brief)
# plus quelques séries complémentaires usuelles pour un outil de backtest
# (emploi, courbe des taux, volatilité, dollar). (series_id FRED, nom)
# ---------------------------------------------------------------------------
MACRO_SERIES = [
    # Taux directeurs / obligataires
    ("FEDFUNDS", "Taux des fonds fédéraux (Fed Funds Rate)"),
    ("DGS3MO", "Taux du Trésor US 3 mois"),
    ("DGS2", "Taux du Trésor US 2 ans"),
    ("DGS10", "Taux du Trésor US 10 ans"),
    ("DGS30", "Taux du Trésor US 30 ans"),
    ("T10Y2Y", "Spread 10 ans - 2 ans (indicateur de récession)"),
    # Inflation
    ("CPIAUCSL", "Indice des prix à la consommation (CPI, tous postes)"),
    ("CPILFESL", "CPI cœur (hors alimentation et énergie)"),
    ("PCEPI", "Indice des prix des dépenses de consommation (PCE)"),
    # Croissance / activité
    ("GDP", "PIB nominal US"),
    ("GDPC1", "PIB réel US"),
    ("INDPRO", "Indice de production industrielle"),
    # Emploi
    ("UNRATE", "Taux de chômage US"),
    ("PAYEMS", "Emplois non agricoles (Nonfarm Payrolls)"),
    # Monnaie / crédit / change
    ("M2SL", "Masse monétaire M2"),
    ("DTWEXBGS", "Indice du dollar US pondéré par les échanges commerciaux"),
    # Logement / sentiment / volatilité
    ("HOUST", "Mises en chantier de logements (Housing Starts)"),
    ("UMCSENT", "Indice de confiance des consommateurs (U. Michigan)"),
    ("VIXCLS", "Indice de volatilité CBOE (VIX)"),
]


def all_yfinance_symbols():
    """Retourne tous les symboles à ingérer via yfinance (actions, indices,
    forex, commodities) sous forme de liste de tuples (symbol, asset_class)."""
    symbols = []
    symbols += [(sym, "equity") for sym, _ in SP500]
    symbols += [(sym, "equity") for sym, _ in CAC40]
    symbols += [(sym, "index") for sym, _ in INDICES]
    symbols += [(sym, "forex") for sym, _ in FOREX_PAIRS]
    symbols += [(sym, "commodity") for sym, _ in COMMODITIES]
    return symbols
