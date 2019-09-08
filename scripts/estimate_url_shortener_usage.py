import datetime

# Customize:
NUM_LINKS_CREATED_THUS_FAR_FOR_ONE_ACCOUNT = 80  # "Total Bitlinks" from https://app.bitly.com/organization/Oj25iZx0iy0/detail
NUM_ACCOUNTS_USED = 20

assert NUM_LINKS_CREATED_THUS_FAR_FOR_ONE_ACCOUNT <= 1000
num_links_created_thus_far = NUM_LINKS_CREATED_THUS_FAR_FOR_ONE_ACCOUNT * NUM_ACCOUNTS_USED
day = datetime.date.today().day
days_in_month = 31
num_links_created_monthly = num_links_created_thus_far * (days_in_month / day)
num_links_created_daily = num_links_created_monthly / days_in_month
num_links_created_hourly = num_links_created_daily / 24

print('Number of links created using all accounts: '
      f'{num_links_created_monthly:.0f}/month, '
      f'{num_links_created_daily:.0f}/day, '
      f'{num_links_created_hourly:.1f}/hour')
print('Number of links created using each account: '
      f'{num_links_created_monthly/NUM_ACCOUNTS_USED:.0f}/month, '
      f'{num_links_created_daily/NUM_ACCOUNTS_USED:.0f}/day, '
      f'{num_links_created_hourly/NUM_ACCOUNTS_USED:.1f}/hour')
