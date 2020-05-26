import datetime
import math

# Customize:
NUM_LINKS_CREATED_THUS_FAR_FOR_ONE_ACCOUNT = 80  # "Total Bitlinks" from https://app.bitly.com/organization/1/detail
NUM_ACCOUNTS_USED = 20
# End of customization

max_num_allowable_links_per_account = 1000
max_num_recommended_links_per_account = 500  # Note: A warning email is sent if usage exceeds this value.
usage_buffer_percentage = 20
assert NUM_LINKS_CREATED_THUS_FAR_FOR_ONE_ACCOUNT <= max_num_allowable_links_per_account
num_links_created_thus_far = NUM_LINKS_CREATED_THUS_FAR_FOR_ONE_ACCOUNT * NUM_ACCOUNTS_USED
day = datetime.date.today().day
days_in_month = 31
num_links_created_monthly = num_links_created_thus_far * (days_in_month / day)
num_links_created_daily = num_links_created_monthly / days_in_month
num_links_created_hourly = num_links_created_daily / 24
print(
    "Number of links created using all accounts are: "
    f"{num_links_created_monthly:.0f}/month, "
    f"{num_links_created_daily:.0f}/day, "
    f"{num_links_created_hourly:.1f}/hour"
)

num_links_created_monthly_per_account = num_links_created_monthly / NUM_ACCOUNTS_USED
num_links_created_daily_per_account = num_links_created_daily / NUM_ACCOUNTS_USED
num_links_created_hourly_per_account = num_links_created_hourly / NUM_ACCOUNTS_USED
print(
    "Number of links created using each account are: "
    f"{num_links_created_monthly_per_account:.0f}/month, "
    f"{num_links_created_daily_per_account:.0f}/day, "
    f"{num_links_created_hourly_per_account:.1f}/hour"
)

num_links_created_monthly_with_buffer = num_links_created_monthly * (1 + (usage_buffer_percentage / 100))
num_recommended_accounts = math.ceil(num_links_created_monthly_with_buffer / max_num_recommended_links_per_account)
print(f"Number of accounts recommended with a +{usage_buffer_percentage}% usage buffer is {num_recommended_accounts}.")
