# Roster Portal Tickets Migration Script

This script is used to migrate tickets from [Assembla](https://assembla.com) to a [GitHub](https://github.com) repository.
It reads data from a text file, processes it, and uses the [GitHub CLI](https://cli.github.com/) to create issues in a specified repository.

You can view the Issues created by this script in this repo as proof of concept and the file that generated it [your-space-2024-03-01.txt](./your-space-2024-03-01.txt). 
* [Issues](https://github.com/MannanM/assembla-to-github/issues)
* [Milestones](https://github.com/MannanM/assembla-to-github/milestones) 
* [Labels](https://github.com/MannanM/Roster-Portal-Tickets/labels)
* Markdown version of the tickets in the [Source](https://github.com/MannanM/assembla-to-github/tree/master/Tickets)

## Features

- Reads data from an Assembla export file and processes it into Python objects.
  - The export file can be obtained from the Assembla 'Space Settings - Tools - Tickets (Settings) - Export and Import - Export your tickets' 
  - https://app.assembla.com/spaces/your-space/tickets/settings/export-and-import
- Creates milestones, labels, and tickets (issues) in a GitHub repository.
- Supports inclusion of comments for tickets in the GitHub issue.
- Assigns tickets to the correct user based on the input data.
- Handles the closing of tickets and milestones based on the input data.

## Requirements

- Python 3
- GitHub CLI

## Usage

1. Ensure that you have Python 3 and GitHub CLI installed on your system.
2. Clone this repository and navigate to the directory containing the script.
3. Update variables at the top of the script for your use case.
   1. `repoName` - The name of the GitHub organization & repository to create the issues in.
   2. `timezone` - The local timezone of the output data. E.g. to use AEST (UTC+10), set this to `timedelta(hours=10)`.
   3. `time_format` - The format of the input date and time. E.g. to use `dd/mm/yyyy hh:mm`, set this to `'%d/%m/%Y %H:%M'`.
   4. `users` - A dictionary of user IDs and their corresponding names. E.g. `{'user_id': 'User Name'}`.
   5. `github_users` - A dictionary of user IDs and their corresponding GitHub usernames. E.g. `{'user_id': 'github_username'}`.
   6. `closed_ticket_status` - A dictionary of ticket statuses and their corresponding issue closed status E.g. `{'status': 'not planned'}`.
      1. The default value is `completed`
   7. `priority` - A dictionary of ticket priorities and their corresponding issue priority. E.g. `{'1': 'Highest', '2': 'High'}`.
4. Run the script with Python: `python migrate.py`

## Known Issues

* Works only with Assembla export files in the format of the provided sample file.
* Does not support attachments or other ticket data.
* Does not support the creation of new users in the GitHub repository.
* Assumes a completely empty GitHub repository.
  * This is so that ticket #1 in Assembla will be created as issue #1 in GitHub.
  * It also assumes there are no Milestones. If there are you need to update `milestone_index` to the next available milestone number +1.
* If you have messed up in some way, and you need to update rather than create, you can comment out the `to_command_array` function and use the `to_update_command_array` function as well as comment out the placeholder creation.

## Contributing

Pull requests are welcome.
