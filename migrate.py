from datetime import datetime, timedelta
import csv
import re
import subprocess
import time

DRY_RUN = True
FILE_NAME = 'your-space-2024-03-01.txt'
REPO_NAME = 'MannanM/assembla-to-github'
TIME_ZONE = timedelta(hours=10)
TIME_FORMAT = '%d/%m/%Y %H:%M:%S'
USERS = {
    'null': 'Unassigned',
    'user1': 'Mannan',
    'user2': 'Tony'
}
GITHUB_USERS = {
    'user1': 'MannanM',
}
CLOSED_TICKET_STATUS = {
    'Invalid': 'not planned',
}
PRIORITY = {
    '1': 'Highest',
    '2': 'High',
    '3': 'Medium',
    '4': 'Low',
    '5': 'Lowest',
}
SUBSTRING_COUNTS = {}
MILESTONES = {}
LABELS = {}
TICKET_STATUS = {}
TICKETS = {}
RATE_LIMIT = 1


class Milestone:
    def __init__(self, name, due_date, user_id, description, is_completed, completed_date):
        self.name = name
        if due_date == 'null':
            self.due_date = None
        else:
            self.due_date = due_date + 'T00:00:00Z'
        self.description = 'Created By ' + USERS[user_id] + '\n' + description
        if is_completed == '0':
            self.state = 'open'
        else:
            self.state = 'closed'
            self.description = self.description + '\n' + 'Completed on ' + completed_date

    def __str__(self):
        return (f'Milestone(name={self.name}, dueDate={self.due_date}, state={self.state}, '
                f'description={self.description})')

    def to_command_array(self, reponame):
        state_ = ['gh', 'api', f'repos/{reponame}/milestones', '-X', 'POST',
                  '-f', f'title={self.name}', '-f', f'description={self.description}']
        if self.due_date is not None:
            state_.append('-f')
            state_.append(f'due_on={self.due_date}')
        return state_

    def to_close_command_array(self, reponame, milestone_id):
        return ['gh', 'api', f'repos/{reponame}/milestones/{milestone_id}', '-X', 'PATCH', '-f', f'state={self.state}']


class Label:
    def __init__(self, name, ticket_id):
        self.name = name
        self.ticket_id = ticket_id

    def __str__(self):
        return f'Label(name={self.name})'

    def __eq__(self, other):
        is_label = isinstance(other, self.__class__)
        return is_label and self.name == other.name

    def __hash__(self):
        return hash(self.name)

    def to_command_array(self, reponame):
        return ['gh', 'label', 'create', self.name, '--repo', reponame]


class Status:
    def __init__(self, name, state):
        self.name = name
        self.open = state == '1'
        self.reason = CLOSED_TICKET_STATUS.get(name, 'completed')


def filter_string(unfiltered_string):
    pre_ = (unfiltered_string
            .replace('\u200B', '')
            .replace('\\u0026', '&')
            .replace('\\u003c', "<")
            .replace('\\u003e', ">")
            .replace('\\n', '\n')
            .replace('\n# ', '\n* ')
            .replace('\nh1. ', '\n# ')
            .replace('\nh2. ', '\n## ')
            .replace('\nh3. ', '\n### ')
            .replace('\nh4. ', '\n#### ')
            .replace('\nh5. ', '\n##### ')
            .replace('\n** ', '\n  * ')
            .replace('\n*** ', '\n    * ')
            .replace('\n**** ', '\n      * ')
            .replace('<pre><code>', '```')
            .replace('</code></pre>', '```')
            )
    pattern = r'\[\[url:(.*?)\|(.*?)\]\]'
    replacement = r'[\2](\1)'
    pre_ = re.sub(pattern, replacement, pre_)
    pattern = r"https://(app|www)\.assembla\.com/spaces/.*/tickets/(\d+)[a-zA-Z0-9-/]*"
    replacement = fr"https://github.com/{REPO_NAME}/issues/\2"
    pre_ = re.sub(pattern, replacement, pre_)
    pattern = r"\[\[image:.*\|(.*?)\]\]"
    replacement = r"image: `\1`"
    pre_ = re.sub(pattern, replacement, pre_)
    # this ensures any ``` are on their own line e.g. foo```bar```baz becomes foo\n```\nbar\n```\nbaz
    pattern = r"([^\n])```"
    replacement = r"\1\n```"
    pre_ = re.sub(pattern, replacement, pre_)
    pattern = r"```([^\n])"
    replacement = r"```\n\1"
    return re.sub(pattern, replacement, pre_)


class Tickets:

    def __init__(self, ticket_id, name, description, priority, created_on, created_by, updated_on, status, assigned_to,
                 worked_hours, milestone):
        self.id = int(ticket_id)
        self.name = filter_string(name)
        self.description = filter_string(description)
        self.labels = []
        self.comments = []
        self.priority = priority
        self.created_on = datetime.fromisoformat(created_on) + TIME_ZONE
        self.updated_on = datetime.fromisoformat(updated_on) + TIME_ZONE
        self.created_by = USERS[created_by]
        # This is a bit ugly because it relies on tickets being after ticket_statuses
        self.status = TICKET_STATUS[status]
        self.assigned_to = USERS[assigned_to]
        if milestone == 'null':
            self.milestone = None
        else:
            self.milestone = MILESTONES[milestone]
        if assigned_to in GITHUB_USERS:
            self.github_assigned_to = GITHUB_USERS[assigned_to]
        else:
            self.github_assigned_to = None
        self.worked_hours = worked_hours

    def __str__(self):
        return f'Ticket(id={self.id}, name={self.name})'

    def add_label(self, label):
        self.labels.append(label)

    def add_comment(self, comment):
        self.comments.append(comment)

    def to_markdown_string(self, full=True):
        header_row = ''
        labels_row = ''
        comments_row = ''
        hours_worked_row = ''
        milestone_row = ''
        if full:
            header_row = '# ' + str(self.id) + ' - ' + self.name
        if len(self.labels) != 0 and full:
            labels_row = '| Labels | ' + ', '.join(self.labels) + ' |\n'
        if len(self.comments) != 0:
            comments_row = '### Comments\n\n' + '\n\n'.join([str(x) for x in self.comments])
        if self.worked_hours != '0.0':
            hours_worked_row = '| Hours Worked | ' + self.worked_hours + ' |\n'
        if self.milestone is not None and full:
            milestone_row = '| Milestone | ' + self.milestone.name + ' |\n'
        return (header_row +
                '\n\n| Attribute | Value |\n| --- | --- |\n'
                '| Status | ' + self.status.name + ' |\n' +
                milestone_row +
                '| Assigned To | ' + self.assigned_to + ' |\n'
                '| Created By | ' + self.created_by + ' |\n'
                '| Created | ' + self.created_on.strftime(TIME_FORMAT) + ' |\n'
                '| Last Updated | ' + self.updated_on.strftime(TIME_FORMAT) + ' |\n'
                '| Priority | ' +
                PRIORITY[self.priority] + ' |\n' +
                labels_row + hours_worked_row + '\n\n' + self.description + '\n\n' +
                comments_row)

    def to_command_array(self, reponame):
        # If you are running on windows and have very large tickets, you may need to add [0:20000] to the ticket_body
        # This will only load the first 20,000 characters in, but will allow the command to run
        ticket_body = self.to_markdown_string(False)
        state_ = ['gh', 'issue', 'create', '--title', self.name,
                  '--body', ticket_body, '--repo', reponame]
        for label in self.labels:
            state_.append('--label')
            state_.append(label)
        if self.github_assigned_to is not None:
            state_.append('--assignee')
            state_.append(self.github_assigned_to)
        if self.milestone is not None:
            state_.append('--milestone')
            state_.append(self.milestone.name)
        return state_

    def to_update_command_array(self, reponame):
        ticket_body = self.to_markdown_string(False)
        state_ = ['gh', 'issue', 'edit', str(MATCHING_TICKET.id), '--title', self.name,
                  '--body', ticket_body, '--repo', reponame]
        for label in self.labels:
            state_.append('--add-label')
            state_.append(label)
        if self.github_assigned_to is not None:
            state_.append('--add-assignee')
            state_.append(self.github_assigned_to)
        if self.milestone is not None:
            state_.append('--milestone')
            state_.append(self.milestone.name)
        return state_

    def to_close_command_array(self, reponame):
        return ['gh', 'issue', 'close', str(MATCHING_TICKET.id), '--repo', reponame, '--reason', self.status.reason]


class TicketComment:

    def __init__(self, description, created_on, created_by):
        self.description = filter_string(description)
        self.created_on = datetime.fromisoformat(created_on) + TIME_ZONE
        self.created_by = USERS[created_by]

    def __str__(self):
        return f'> Comment by {self.created_by} at {self.created_on.strftime(TIME_FORMAT)}\n\n{self.description}'


def read_csv(string_line, name):
    csv_line = string_line[(len(name) + 3):-2].replace('\\"', '╣"')
    return csv.reader([csv_line], escapechar='╣')


def execute(command_array, orig_count):
    if DRY_RUN:
        return orig_count
    try:
        result = subprocess.run(command_array, capture_output=True, text=True, check=True)
        if len(result.stdout) > 0:
            print(f'{result.stdout.strip()}')
    except subprocess.CalledProcessError as e:
        if e.stderr.find('was submitted too quickly') != -1:
            input('Rate limit exceeded. Wait some time and hit enter.')
            return execute(command_array, orig_count)
        raise SystemExit(f'Return Code: {e.returncode} {e.stderr}') from e
    if orig_count % 9 == 0:
        time.sleep(60)
    return orig_count + 1


with open(FILE_NAME, 'r', encoding='utf-8') as file:
    for line in file:
        split = line.split(',')
        typeOfEntity = split[0]
        if not typeOfEntity.endswith(':fields'):
            if typeOfEntity in SUBSTRING_COUNTS:
                SUBSTRING_COUNTS[typeOfEntity] += 1
            else:
                SUBSTRING_COUNTS[typeOfEntity] = 1
            if typeOfEntity.startswith('milestones'):
                for row in read_csv(line, 'milestones'):
                    MILESTONES[row[0]] = Milestone(row[2], row[1], row[5], row[7], row[8], row[9])
            elif typeOfEntity.startswith('workflow_property_vals'):
                for row in read_csv(line, 'workflow_property_vals'):
                    LABELS[row[0]] = Label(row[4], row[1])
            elif typeOfEntity.startswith('ticket_statuses'):
                for row in read_csv(line, 'ticket_statuses'):
                    TICKET_STATUS[row[0]] = Status(row[2], row[3])
            elif typeOfEntity.startswith('tickets'):
                for row in read_csv(line, 'tickets'):
                    TICKETS[row[0]] = Tickets(
                        row[1], row[5], row[7], row[6], row[8], row[2], row[9],
                        row[19], row[3], row[23], row[10]
                    )
            elif typeOfEntity.startswith('ticket_comments'):
                for row in read_csv(line, 'ticket_comments'):
                    if row[5] != '' and row[5] != 'null':
                        TICKETS[row[1]].add_comment(TicketComment(row[5], row[4], row[2]))

for key, value in SUBSTRING_COUNTS.items():
    print(f'{key}: {value}')

for key, value in MILESTONES.items():
    print(f'Creating: {value}')
    RATE_LIMIT = execute(value.to_command_array(REPO_NAME), RATE_LIMIT)

distinct_labels = set(value for value in LABELS.values())
for value in distinct_labels:
    print(f'Creating: {value}')
    RATE_LIMIT = execute(value.to_command_array(REPO_NAME), RATE_LIMIT)

for key, value in LABELS.items():
    TICKETS[value.ticket_id].add_label(value.name)

last_ticket = list(TICKETS.values())[-1]
for ticket_num in range(1, last_ticket.id + 1):
    MATCHING_TICKET = None
    for ticket in TICKETS.values():
        if ticket.id == ticket_num:
            MATCHING_TICKET = ticket
            break
    if MATCHING_TICKET:
        # this will create a .md file of the tickets in the Tickets folder
        # helpful for debugging or if you want an offline copy
        with open(f'./Tickets/{str(MATCHING_TICKET.id).zfill(4)}.md', 'w', encoding='utf-8') as f:
            f.write(MATCHING_TICKET.to_markdown_string())
        # If you need to update, you can use the line below instead of the normal to_command_array
        # You will need to comment out the placeholder creation line below as well
        # count = execute(matching_ticket.to_update_command_array(repoName), count)
        RATE_LIMIT = execute(MATCHING_TICKET.to_command_array(REPO_NAME), RATE_LIMIT)
        if not MATCHING_TICKET.status.open:
            print(" - Closing ticket: " + str(MATCHING_TICKET.id))
            RATE_LIMIT = execute(MATCHING_TICKET.to_close_command_array(REPO_NAME), RATE_LIMIT)
    else:
        # This is to keep the numbers consistent with Assembla
        # E.g. if you create an issue with ID 1000, then the next issue will be 1001
        print('No ticket found with the given ID = ' + str(ticket_num))
        RATE_LIMIT = execute(['gh', 'issue', 'create', '--title', 'Placeholder', '--body',
                              'Placeholder', '--repo', REPO_NAME], RATE_LIMIT)
        RATE_LIMIT = execute(['gh', 'issue', 'close', str(ticket_num), '--repo', REPO_NAME,
                              '--reason', 'not planned'], RATE_LIMIT)

# Close milestones
for index, (key, value) in enumerate(MILESTONES.items()):
    # If you already have milestones created in the repo, you can change + 1 to highest milestone # +1
    milestone_index = index + 1
    if value.state == 'closed' and milestone_index != 'Unknown':
        print(f'Closing milestone id: {milestone_index} for {value}')
        RATE_LIMIT = execute(value.to_close_command_array(REPO_NAME, milestone_index), RATE_LIMIT)
