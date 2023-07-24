# %%

import pandas as pd

def extract_data_from_txt():
    # Load the text file
    with open("/home/gyasis/Documents/code/Herself/data/data.txt", 'r') as file:
        # Convert file lines to a list and filter out empty lines
        lines = [line.strip() for line in file.readlines() if line.strip() != '']

    # Data list to hold extracted information
    data = []
    current_person = {
        "name": None,
        "specialty": None,
        "email": None,
        "phone": None,
        "distance": None
    }

    # Variable to track if the next line should be a name
    next_is_name = True

    for line in lines:
        # Updated Rules for extraction
        if next_is_name:
            current_person["name"] = line
            next_is_name = False
        elif "?" in line:
            current_person["specialty"] = line.replace("?", "")
        elif "@" in line:
            current_person["email"] = line
        elif any(char.isdigit() for char in line) and "miles" not in line:
            current_person["phone"] = line
        elif "miles" in line:
            current_person["distance"] = line
            data.append(current_person)
            current_person = {
                "name": None,
                "specialty": None,
                "email": None,
                "phone": None,
                "distance": None
            }
            next_is_name = True

    # Convert list to DataFrame
    df = pd.DataFrame(data)

    # Return the data for verification
    return df

# Example usage:
df = extract_data_from_txt()
print(df)

# %%
import pandas as pd

def extract_data_from_txt_v11():
    # Load the text file
    with open("/home/gyasis/Documents/code/Herself/referral/data2.txt", 'r') as file:
        content = file.read()

    # Split content into blocks
    blocks = [block.strip() for block in content.split("\n \n \n") if block.strip()]

    data = []

    for block in blocks:
        lines = [line.strip() for line in block.split("\n") if line.strip()]

        # The first line is the specialty type
        current_specialty = lines[0].rstrip(':')
        lines = lines[1:]
        
        current_entry = {
            "Specialty": current_specialty,
            "Name of Organization": "not available",
            "Name": "not available",
            "Phone Number": "not available",
            "Website": "not available",
            "Email": "not available",
            "Notes": "not available",
            "Location": "not available"
        }

        for line in lines:
            if line.startswith("name:"):
                if current_entry["Name"] != "not available":
                    data.append(current_entry)
                    current_entry = {
                        "Specialty": current_specialty,
                        "Name of Organization": "not available",
                        "Name": "not available",
                        "Phone Number": "not available",
                        "Website": "not available",
                        "Email": "not available",
                        "Notes": "not available",
                        "Location": "not available"
                    }
                current_entry["Name"] = line.split("name:", 1)[1].strip()
            elif line.startswith("org:"):
                current_entry["Name of Organization"] = line.split("org:", 1)[1].strip()
            elif line.startswith("telephone:") or line.startswith("phone:") or line.startswith("number:"):
                current_entry["Phone Number"] = line.split(":")[1].strip()
            elif line.startswith("web:"):
                current_entry["Website"] = line.split("web:", 1)[1].strip()
            elif line.startswith("notes:"):
                current_entry["Notes"] = line.split("notes:", 1)[1].strip()
            elif line.startswith("location:"):
                current_entry["Location"] = line.split("location:", 1)[1].strip()
        
        if current_entry["Name"] != "not available":
            data.append(current_entry)

    # Change specialty for entries after the first to "Psychotherapists"
    for entry in data[1:]:
        entry["Specialty"] = "Psychotherapists"

    df2 = pd.DataFrame(data)
    return df2

df2 = extract_data_from_txt_v11()
print(df2)




# %%
import pandas as pd
import re

# Path to your data file
path = "/home/gyasis/Documents/code/Herself/referral/data3.txt"

# Reading from the file
with open(path, 'r') as file:
    data = file.read()

lines = data.strip().split("\n")

specialty = None
current_org = {}
entries = []

for idx, line in enumerate(lines):
    # Check if the line starts with a number, indicating a new specialty.
    if re.match(r"^\d+\.?", line):
        specialty = line.split(" ", 1)[-1].strip()  # Take only the part after the number
        continue

    # Check for 'org:' or 'name:'
    if line.startswith("org:") or line.startswith("name:"):
        # If there's an existing org, save it to entries.
        if current_org:
            entries.append(current_org)
            current_org = {}
        
        current_org['Specialty'] = specialty
        current_org['Name of Organization'] = line.split(":", 1)[1].strip()

    # Capture other attributes
    elif "web:" in line:
        current_org['Website'] = line.split(":", 1)[1].strip()
    elif "location:" in line:
        current_org['Location'] = line.split(":", 1)[1].strip()
    elif "notes:" in line:
        current_org['Notes'] = line.split(":", 1)[1].strip()
    elif "name:" in line:
        current_org['Name'] = line.split(":", 1)[1].strip()

# Add the last org, if available.
if current_org:
    entries.append(current_org)

# Convert to DataFrame with specific columns
df3 = pd.DataFrame(entries, columns=["Specialty", "Name of Organization", "Name", "Website", "Location", "Notes", "Phone Number", "Email"])
print(df3)


# %%
import pandas as pd
import re

# ... [Your data extraction functions and their calls]

# Function to standardize column names
def standardize_columns(df):
    df.columns = [col.upper().replace(" ", "_") for col in df.columns]
    # Check for duplicate columns
    if len(df.columns) != len(set(df.columns)):
        raise ValueError(f"Duplicate columns detected in dataframe: {df.columns}")
    return df


# Standardize the columns of each dataframe
df = standardize_columns(df)
df2 = standardize_columns(df2)
df3 = standardize_columns(df3)

# Define the desired columns structure based on df2
desired_columns = [
    "SPECIALTY", "NAME_OF_ORGANIZATION", "NAME", 
    "PHONE_NUMBER", "WEBSITE", "EMAIL", 
    "NOTES", "LOCATION"
]

# Ensure the columns in each dataframe match the desired structure.
# Add any missing columns with 'not available' as their default value.
def conform_df_to_columns(df, columns):
    for col in columns:
        if col not in df.columns:
            df[col] = "not available"
    return df[columns]

df = conform_df_to_columns(df, desired_columns)
df2 = conform_df_to_columns(df2, desired_columns)
df3 = conform_df_to_columns(df3, desired_columns)

# Vertically stack the dataframes
final_df = pd.concat([df, df2, df3], ignore_index=True)

print(final_df)


# %%
def find_potential_duplicates(df, column, threshold=85):
    potential_duplicates = []
    
    for idx in tqdm(range(len(df)), desc=f"Checking {column}"):
        for next_idx in range(idx+1, len(df)):
            if pd.isnull(df.at[idx, column]) or pd.isnull(df.at[next_idx, column]):
                continue
            similarity = fuzz.ratio(df.at[idx, column], df.at[next_idx, column])
            if similarity >= threshold:
                potential_duplicates.append((df.iloc[idx], df.iloc[next_idx]))
    
    return potential_duplicates

# Check for potential duplicates in the relevant columns
columns_to_check = ["NAME_OF_ORGANIZATION", "PHONE_NUMBER", "NAME"]
duplicate_pairs = []

for col in columns_to_check:
    duplicates = find_potential_duplicates(final_df, col)
    for pair in duplicates:
        duplicate_pairs.append(pair)

# Convert potential duplicate pairs to DataFrame for comparison
duplicates_df = pd.concat([pd.DataFrame([pair[0]]), pd.DataFrame([pair[1]])] for pair in duplicate_pairs).reset_index(drop=True)

print(duplicates_df)
# %%
