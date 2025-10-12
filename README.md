

# CampaignIQ 📈

CampaignIQ is a robust analytical solution designed to move beyond simple correlations and measure the true causal impact of public health campaigns. It uses a state-of-the-art causal inference pipeline to provide health organizations with a precise, unbiased measure of campaign ROI and actionable insights for strategic resource allocation.

![Project Output Screenshot](./v1/images/output_1.jpg)

![Project Output Screenshot](./v1/images/output_3.jpg)

![Project Output Screenshot](./v1/images/output_4.jpg)

![Project Output Screenshot](./v1/images/output_2.jpg)

-----

## The Problem

A health organization needs to rigorously evaluate the effectiveness of its health awareness campaign. Standard performance metrics, such as comparing booking rates between targeted and non-targeted groups, are unreliable as they fail to distinguish correlation from causation. These simple comparisons are often contaminated by confounding variables like a patient's district, age, or pre-existing conditions, leading to a biased and misleading assessment of the campaign's true impact.

Consequently, decision-makers cannot confidently determine the campaign's return on investment or strategically allocate resources for future initiatives. They require a robust analytical solution that can isolate the true causal effect of the campaign on booking rates and identify the most responsive demographic segments.

-----

## The Solution

The proposed solution is a causal inference pipeline designed to accurately measure the true impact of the public health campaign while correcting for confounding variables. It utilizes a state-of-the-art **AIPW (Augmented Inverse Propensity Weighting)** estimator, a doubly-robust method that provides a reliable estimate even if one of its underlying models is misspecified.

To ensure statistical rigor and prevent bias, the pipeline employs **k-fold cross-fitting** when training its machine learning components. Beyond calculating the overall **Average Treatment Effect (ATE)**, the solution drills down to identify the most responsive patient subgroups by computing **Conditional Average Treatment Effects (CATEs)**.

The final output is a comprehensive analysis that includes a precise, unbiased measure of campaign ROI, critical diagnostic plots to validate assumptions, and an actionable list of high-performing segments.

-----

## Target Audience

1.  **Program Managers & Strategists:** The decision-makers who use the ROI and segment recommendations to justify budgets and optimize future campaigns for maximum impact.
2.  **Data Scientists & Analysts:** The technical experts who build, validate, and maintain the analytical engine, ensuring the results are statistically sound by scrutinizing its methodology and diagnostics.
3.  **Health Officials & Funders:** The stakeholders who require clear, defensible impact summaries to ensure accountability and make informed decisions on future investments and public health policy.

-----

## Getting Started

To get a local copy up and running, follow these simple steps.

### Prerequisites

  * Node.js and npm
  * Python 3.x and pip

### **Configuration: Add Hugging Face Token** 🔑

This project requires a Hugging Face token to download the necessary machine learning models from the Hub. You can provide it in one of two ways:

#### **Method 1: Using an Environment File (Recommended)**

This is the most secure method and prevents your secret token from being accidentally committed to version control.

1.  Create a new file named `.env` in the root directory of the project (`v1/.env`).
2.  Add the following line to the file, replacing the placeholder with your actual token:
    ```
    HF_TOKEN="your_hugging_face_token_here"
    ```
3.  Ensure `.env` is listed in your `.gitignore` file.

#### **Method 2: Directly in the Code (Quick Setup)**

For a faster setup, you can add the token directly into the backend script.

1.  Open the file: `v1/backend/causal_impact.py`.
2.  Navigate to approximately **line 74** and replace the default token string with your own:
    ```python
    # Find this line
    hf_token = os.environ.get("HF_TOKEN", "<your_token_here")

    # Replace the default token with your own, like this:
    hf_token = os.environ.get("HF_TOKEN", "your_actual_hugging_face_token")
    ```

### Installation & Execution

1.  **Clone the repo**

    ```sh
    git clone https://github.com/MOHAMEDAHSAN/CampaignIQ.git
    cd CampaignIQ
    ```

2.  **Install and run the frontend** (in a new terminal window)

    ```sh
    cd v1
    npm install
    npm run dev
    ```

3.  **Install dependencies and run the backend** (in another terminal window)

    ```sh
    # Make sure you are in the root CampaignIQ directory
    pip install -r requirements.txt  # You may need to create a requirements.txt file
    python v1/backend/app.py
    ```

-----
### Sample Dataset


[`campaign_dataset.csv`](https://github.com/MOHAMEDAHSAN/CampaignIQ/blob/main/v1/backend/campaign_dataset.csv) file located in the `v1/backend/` directory. 
## License

Distributed under the **Apache License**. See `LICENSE` for more information.


