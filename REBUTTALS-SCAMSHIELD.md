

| The collected data is then preprocessed through operations such as duplicate removal, URL normalization, missing value handling, feature scaling, and dataset balancing by SMOTE \\cite{chawla2002smote} to generate high-quality training data for machine learning. HOW DID YOU NORMALIZE URL? HOW DID YOU HANDLE MISSING VALUES? DATASET BALANCING BY SMOTE ? DETAILS PLEASE |
| :---- |
|  |
| These features are first **numerically encoded** before they are fed into the model for training and prediction. Detail? How? |
|  |
| Dynamic crawling?which crawler is used? Its working? Why did you called it lightweight?  |
|  |
| Difference b/w backend detection engine? What is it? Explain its working? As you said” The gathered data is sent to the backend detection engine, where heuristic analysis and machine learning classification are carried out” |
|  |
| What is DOM. Explain in 2-3 lines . its importance it analyzing content? Or how important this is in your project when extracting feature |
|  |
| Sample of JSON ? please share pdf imga (JSON format and sent to the backend detection engine for further processing.) what further processing? Describe stage exactly |
|  |
| Hybrid detection engine? Why did you called hybrid? Combination of what? |
|  |
| White list checking vs blacklist? Difference? Which is relevant or more important? |
|  |
| Why rule based heuristic is important? What could be the other ways?  |
|  |
| Why did you choose random forest? Why not other classifiers?  |
|  |
| Based on the overall risk score resulting from these different analyses, the website is labeled Safe, Suspicious, or Malicious. HOW DID YOU CALCULATE RISK SOCRE? EXPLAIN IN DETAIL (IT’S THE MOST CRUCIAL PART). WHAT WAS THE THRESHOLD? HOW IT WAS SELECTED?  According to the determined risk score, the website will be categorized as Safe, Suspicious, or Phishing ? what is the determined score. I need detail here  |
|  |
| Share screenshot(pdf version) of safe previw mode. If the extension is available online please share link |
|  |
| What is docker? What is its container? Explain in scamshield prespective |
|  |
| The User Interface module shows phishing alerts(in the form of what? Share figure), classification results, extracted threat indicators(how?), and risk scores(calculation detail)? Please explain |
|  |
| If the website is judged to be dangerous, the Safe Preview feature will load the webpage within an isolated Docker container . HOW DANGEROUD? WHAT ARE THE PARAMETERS OF CALLING IT DANGEROUS |
|  |
| ScamShield employs a lightweight local inspection module combined with an asynchronous backend for heavy ML inference. . explain lightweight local inspection module and asynchronous backend for what type of heavy interference and how did you handle it? |
|  |
| The working of the extension is browser-centric i.e. it constantly checks browser activity for signs of phishing and does so in time for the attack to be averted How did it check constantly? Explain its working detail? |
|  |
| Also, it is built to carry out low power analysis. What is low-power analysus? How can you label low power ? what are the parameters? |
|  |
| list down all the APIs you have used and its description (why those apis are relevant) |
|  |
| As a website loads, the extension saves the full URL of the visited site including protocol, domain name, path, and query parameters (SHARE CODE SNIPPET OR SCREENSHOT FIGURE MUST BE IN PDF) |
|  |
| WHAT IS lexical feature ? importance? |
|  |
| this study has chosen to focus on major elements like hyperlinks, fields, iframes, buttons, and images. WHY THESE? IMPORTANCE? REASON MISSING |
|  |
| Some kinds of redirects that may be detected on the frontend level are meta-refresh, JavaScript window.location, URL shortening, and onclick event revisions. The redirect analysis helps track phishing attacks that forward users to malicious domains silently. DID YOU HANDLE ALL THESE?  |
|  |
| the frontend sends the data, packed as a JSON message, to the backend Flask REST API through the network. NETWORK DETAIL? |
|  |
| The server then takes the information and applies heuristic analysis and machine learning classification . SERVER DETAIL? HEAURISTIC ANALYSIS DETIAL? |
|  |
| promptly sent back; the extension will then notify the user by means of visual signals embedded. EXPLAIN VISUAL SUGNALS EMBEDDED. ITS WORKING IN YOUR PROJECT |
|  |
| It is responsible for cleaning and standardizing URLs by, for example, converting texts to lower case, stripping off unnecessary characters, normalizing protocols, and obtaining essential URL parts such as domain names and query parameters. SHARE CODE SNIPPET? DIAGRAM ? SAMPLE JSON FORMAT BEFORE AND AFTER  |
|  |
| According to the feature vector that has been generated . SHARE YOUR FEATURE VECTOR FIGURE AND EXPLAIN IT |
|  |
| That is where analyzed websites, timestamps, risk scores, and phishing classification results are stored \- a sort of log for monitoring and analysis. SHARE SCREENSHOT OF LOGS AND EXPLAIN IN DETAIL |
|  |
| Numerical feature vectors produced as a result of preprocessing and feature engineering are stored here for later use in model evaluation and retraining. EXPLAIN FEATURE ENGINEERING METHOD ALOG IN DETAIL |
|  |
| confidence scores? EXPLAIN IN DETAIL |
|  |
| SHARE SAFE PREVIEW LOGS DIAGRAM AND EXPLAIN IN DETAIL |
|  |
| USER INTERACTION LOGS? |
|  |
| WHY Selenium WebDriver? WHAT IS IT? ITS ROLE/IMPORTANCE? |
|  |
| Right after the URL is recognized as suspicious, the system creates a small-sized and isolated Docker container \\cite{b15} on the fly. WXPLAIN HOW? |
|  |
| This container offers a perfectly sandboxed environment, where all malicious scripts or harmful activities stay inside it and can't escape to affect user device or the host system. WHICH SANDBOX? |
|  |
| Once the screenshot is captured and transmitted, the container is also automatically stopped and deleted. AUTOMATICALLY? HOW? |
|  |
| Using high-level Docker container? HOW MANY DOCKERS DID YOU USE? ARE ALL OF THESE ARE SAME OR DIFFERENT? THEIR NAME? |
|  |
| The dataset is composed of different URL attributes such as lexical, structural, and domain-level which are most often utilized in phishing detection mechanisms. SHARE SAMPLE URL FOR ALL THESE IN FIGURE AND EXPLAIN. ADD ONE FIGURE FOR LEXICAL, ONE FOR STRUCTURAL AND ONE FOR DOMAIN-LEVEL |
|  |
| Prior to the training process, the dataset was thoroughly cleaned to exclude any noisy and duplicate records. WHICH ALGO USED FOR NOISY AND REDUNDANT DATA REMOVAL? |
|  |
| We dropped all records where feature values were either incomplete or corrupted. AFTER REMOVING SHARE DATASET RECORD LEFT?  |
|  |
| The system presented here retrieves 17 characteristics of URLs and the document object model (DOM), which are of four types: lexical, structural, and DOM-based features. WHAT ARE THE 17 CHARACTERISTICS? |
|  |
| JAVACRIPT EVEN HANDLER? LIST ALL EVENTS YOU HAVE HANDLED |
|  |
| Upon obtaining of all relevant behavior and features, the crawler organizes the data in JSON, which is a good format for interchanging the web data also due to its simplicity. JSON FORMAT FIGURE? |
|  |
| EXPLAIN hybrid filtering approach |
|  |
| reference list of trustworthy sites? WHERE DID YOU GET THOSE TRUSTWORTHY SITES? HOW DID YOU VERIFY ITS TRUSTWRTHY? IS THE NUMBER AVAILABLE ONLINE? SHRE LINK? Examples of such sites are Alexa Top Sites and well-known service providers. ALEXA REFERENCE? AND ALL OTHERS YOU HAVE USED IF POSSIBLE? NAME OF WELL KNOWN SERVICE PROVIDERS |
|  |
| If there are telltale signs of phishing that have been used lately. Telltale signs? Means what? |
|  |
| Those signs include very long URLs, strange subdomain setups, presence of suspicious words, high URL randomness, use of URL shorteners, uncommon port numbers, and hidden iframe usage. In total, each identified anomaly adds to a weighted heuristic risk score that indicates the URL's malicious tendency. Share table where you add SCORE/ WEIGHT TO THESE SIGNS. Which has the highest score and why? Which algo used for scoring or weight assign? |
|  |
| StandardScaler normalization? What is it? |
|  |
| Feature-based voting allows the model to produce a risk score and categorize the webpage into Safe, Suspicious, or Phishing. Explain feature based voting? |
|  |
| light-weight rule-based detections. LIGHTWEIGHT HOW? |
|  |
| WHY DIDN’T YOU USE NAÏVE BAYES OR LGBM |
|  |
| ADD LATENCY PARAMETERS ITS FORMULA. HOW DID YOU CALCULATE?  |
|  |
| TRAINING TIME ? EXPLAIN THIS PARAMTER? HOW IT WAS CALCULATED? |
|  |
| SHARE PDF OF FIGURE 4 SEPARATELY WITH ME. YOU HAVE USED XGBOOST, LGBM RF AND DID NOT MENTION IT IN PAPER? |
|  |
|  |

