# Trilo Bot Command Knowledge Base

This document contains comprehensive information about all Trilo Bot commands for AI-powered help responses.

## Attribute Point System Commands

### For Users

#### `/attributes my-points`
**Description:** Check your current attribute point balance.
**Usage:** Simply type `/attributes my-points` - no parameters needed.
**Example:** `/attributes my-points`
**Response:** Shows your available points (e.g., "You currently have 5 attribute points available.")

#### `/attributes request`
**Description:** Submit a request to spend your points on player upgrades.
**Parameters:**
- `player`: Position & name of the player you're upgrading (e.g., "QB John Smith")
- `attribute`: The attribute you're increasing (select from dropdown menu)
- `amount`: How many points you want to spend (type the number only)
**Usage:** `/attributes request player:QB John Smith attribute:Speed (SPD) amount:3`
**Important Notes:**
- You must have enough points available
- Commissioners must approve all requests
- You can cancel pending requests with `/attributes cancel-request`
**Example:** `/attributes request player:HB Mike Johnson attribute:Speed (SPD) amount:2`

#### `/attributes cancel-request`
**Description:** Cancel one of your pending attribute upgrade requests.
**Parameters:**
- `request_number`: The # of the request you want to cancel
**Usage:** `/attributes cancel-request request_number:5`
**Note:** You can only cancel your own pending requests.

#### `/attributes requests-history` or `/attributes history`
**Description:** View your own point request history (or others if you're a commissioner).
**Parameters:**
- `user`: (Optional) Whose history you want to view. Leave blank to view your own.
**Usage:** `/attributes history` or `/attributes history user:@username`
**Response:** Shows up to 10 most recent requests with status (approved, denied, pending).

### For Commissioners

#### `/attributes give`
**Description:** Award attribute points to users.
**Parameters:**
- `users`: Mention users with @ (can mention multiple users)
- `amount`: Amount of points to award to each user
- `reason`: Why are you giving these points?
- `note`: (Optional) Add a note about upgrade rules or limits
**Usage:** `/attributes give users:@user1 @user2 amount:5 reason:Weekly reward note:Max 2 upgrades per week`
**Important:** Users receive DM notifications when points are given.

#### `/attributes give-role`
**Description:** Give attribute points to all members of a specific role.
**Parameters:**
- `role`: The role whose members will receive points
- `amount`: Amount of points to award to each role member
- `reason`: Why are you giving these points?
- `note`: (Optional) Add a note about upgrade rules or limits
**Usage:** `/attributes give-role role:@Active Members amount:3 reason:Participation bonus`

#### `/attributes approve-request`
**Description:** Approve a pending upgrade request.
**Parameters:**
- `request_number`: Select a pending request to approve (autocomplete available)
**Usage:** `/attributes approve-request request_number:5`
**Note:** System checks if user has enough points before approval.

#### `/attributes approve-all`
**Description:** Approve all pending upgrade requests (optionally filtered by user).
**Parameters:**
- `user`: (Optional) Whose requests you want to approve. Leave blank to approve all users.
**Usage:** `/attributes approve-all` or `/attributes approve-all user:@username`
**Note:** All requests must have sufficient points available.

#### `/attributes deny-request`
**Description:** Deny a pending upgrade request.
**Parameters:**
- `request_number`: Select a pending request to deny (autocomplete available)
- `reason`: (Optional) Reason for denying this request
**Usage:** `/attributes deny-request request_number:5 reason:Insufficient points`

#### `/attributes deny-all`
**Description:** Deny all pending upgrade requests (optionally filtered by user).
**Parameters:**
- `user`: (Optional) Whose requests you want to deny. Leave blank to deny all users.
- `reason`: (Optional) Reason for denying these requests
**Usage:** `/attributes deny-all reason:Season ended` or `/attributes deny-all user:@username reason:Invalid request`

#### `/attributes revoke`
**Description:** Manually revoke attribute points from a user.
**Parameters:**
- `user`: The user to revoke points from
- `amount`: Amount of points to revoke
- `reason`: (Optional) Reason for revoking these points
**Usage:** `/attributes revoke user:@username amount:2 reason:Correction`

#### `/attributes revoke-all-from-user`
**Description:** Reset a user's available attribute points to 0.
**Parameters:**
- `user`: The user whose points you want to reset
- `reason`: (Optional) Reason for revoking all their points
**Usage:** `/attributes revoke-all-from-user user:@username reason:Reset for new season`

#### `/attributes check-user`
**Description:** Check how many attribute points a user has.
**Parameters:**
- `user`: The user whose points you want to check
**Usage:** `/attributes check-user user:@username`

#### `/attributes check-all`
**Description:** Check all users and their available attribute points.
**Usage:** `/attributes check-all` - no parameters needed
**Response:** Lists all users with points, sorted by amount (highest first).

#### `/attributes requests-list` or `/attributes pending`
**Description:** View all pending attribute upgrade requests.
**Usage:** `/attributes pending` - no parameters needed
**Response:** Lists all pending requests with request number, user, player, attribute, and amount.

#### `/attributes clear-all`
**Description:** Clear all attribute points from all users in the server.
**Usage:** `/attributes clear-all` - requires confirmation
**Warning:** This action cannot be undone!

## Team Management Commands

### For All Users

#### `/teams who-has`
**Description:** Check who owns a specific team.
**Parameters:**
- `team`: The team name to check
**Usage:** `/teams who-has team:Oregon`

#### `/teams list-all`
**Description:** See all team assignments in the league.
**Usage:** `/teams list-all` - no parameters needed

### For Commissioners

#### `/teams assign-user`
**Description:** Assign a user to a team.
**Parameters:**
- `user`: The user to assign
- `team`: The team name
**Usage:** `/teams assign-user user:@username team:Oregon`

#### `/teams unassign-user`
**Description:** Remove a user from their team.
**Parameters:**
- `user`: The user to unassign
**Usage:** `/teams unassign-user user:@username`

#### `/teams clear-team`
**Description:** Clear a team's user assignment.
**Parameters:**
- `team`: The team name
**Usage:** `/teams clear-team team:Oregon`

#### `/teams clear-all-assignments`
**Description:** Wipe all team assignments.
**Usage:** `/teams clear-all-assignments` - requires confirmation

## Matchup Commands

### For All Users

#### `/matchups list-all`
**Description:** List all matchups under a specific category, showing which users are playing which teams.
**Parameters:**
- `category_name`: The name of the category containing matchup channels
**Usage:** `/matchups list-all category_name:Week 1`
**Response:** Shows all matchups in the format "Team1 vs Team2" with user mentions or "CPU" for unassigned teams, plus any status emojis (✅, 🎲, ☑️)

### For Commissioners

#### `/matchups create-from-text`
**Description:** Create matchup channels manually by entering matchups as text. You can create up to 20 matchups per command (if you need more, run the command again).
**Parameters:**
- `category_name`: The category name (e.g., "Week 1"). You can type a new name or select from existing categories.
- `game_status`: (Optional) Set to True to show outcome tracking reactions in each matchup
- `roles_allowed`: (Optional) Comma-separated list of role names allowed to view the category
- `matchup_1` through `matchup_20`: Individual matchup entries in format "Team1 vs Team2"
**Usage:** `/matchups create-from-text category_name:Week 1 matchup_1:Oregon vs Washington matchup_2:Alabama vs Georgia game_status:True`
**Important Notes:**
- Format: "Team1 vs Team2" (use " vs " with spaces)
- If category doesn't exist, it will be created
- If category exists, new matchup channels will be added to it
- Duplicate channel names will be skipped

#### `/matchups create-from-image`
**Description:** Create matchups by uploading schedule images. The bot uses AI to extract matchup information from images. You can upload up to 5 images at once.
**Parameters:**
- `category_name`: The category name (e.g., "Week 1"). You can type a new name or select from existing categories.
- `image1`: Upload first image containing matchup information (required)
- `image2`: (Optional) Upload second image
- `image3`: (Optional) Upload third image
- `image4`: (Optional) Upload fourth image
- `image5`: (Optional) Upload fifth image
- `game_status`: (Optional) Set to True to show outcome tracking reactions in each matchup
- `roles_allowed`: (Optional) Comma-separated list of role names allowed to view the category
**Usage:** Upload an image of your schedule and the bot will extract matchups automatically. You'll see a preview before confirming creation.
**Important Notes:**
- The bot extracts team names and matchups from the image using AI
- CPU vs CPU games are automatically skipped (no channels created)
- You'll see a preview of extracted matchups before confirming
- If multiple images are uploaded, matchups from all images are combined

#### `/matchups delete`
**Description:** Delete one or more matchup categories. This deletes ALL matchup channels within the specified categories. You can delete up to 5 categories at once.
**Parameters:**
- `category_1`: The first category to delete (required)
- `reuse_category`: Whether to keep the category for future use (True = keep category but delete all channels, False = delete everything including category)
- `category_2`: (Optional) Second category to delete
- `category_3`: (Optional) Third category to delete
- `category_4`: (Optional) Fourth category to delete
- `category_5`: (Optional) Fifth category to delete
**Usage:** 
- `/matchups delete category_1:Week 1 reuse_category:False` - Completely deletes Week 1 category and all its matchup channels
- `/matchups delete category_1:Week 1 reuse_category:True` - Deletes all matchup channels in Week 1 but keeps the category for future use
- `/matchups delete category_1:Week 1 category_2:Week 2 reuse_category:False` - Deletes multiple categories at once
**Important Notes:**
- This command deletes ENTIRE CATEGORIES, not individual matchups
- All matchup channels within the category will be deleted
- If `reuse_category` is True, the category name is kept but all channels are removed
- If `reuse_category` is False, both the category and all channels are permanently deleted
- Requires confirmation before deletion

#### `/matchups tag-users`
**Description:** Automatically tag users in matchup channels based on their team assignments. Sends a message in each matchup channel mentioning the users who own the teams.
**Parameters:**
- `category_name`: The name of the category containing the matchup channels
**Usage:** `/matchups tag-users category_name:Week 1`
**Important Notes:**
- Only works on channels with "-vs-" in the name
- Tags both users if both teams are assigned
- If a team is CPU (no user assigned), it will show "CPU" instead of a mention

#### `/matchups sync-records`
**Description:** Update matchup messages in a category to reflect current team records. Only works if record tracking is enabled for the server.
**Parameters:**
- `category_name`: The name of the matchup category to update
**Usage:** `/matchups sync-records category_name:Week 1`
**Important Notes:**
- Only works if record tracking is enabled (`/settings set setting:record_tracking_enabled new_value:on`)
- Updates existing "Game Status Tracker" messages in matchup channels
- Shows current win/loss records for each team in the matchup
- If a team has no user assigned, it shows "(CPU)" instead of a record

#### `/matchups make-public`
**Description:** Make a matchup category public and sync all its channels. Makes all channels visible to everyone in the server.
**Parameters:**
- `category_name`: The category name to make public
**Usage:** `/matchups make-public category_name:Week 1`
**Important Notes:**
- Sets the category and all its channels to be visible to everyone
- Syncs permissions for all child channels

#### `/matchups make-private`
**Description:** Make a matchup category private and choose who can view it. Restricts visibility to specific roles.
**Parameters:**
- `category_name`: The category to make private
- `roles_allowed`: Comma-separated list of role names allowed to view the category
**Usage:** `/matchups make-private category_name:Week 1 roles_allowed:Commish,Admin`
**Important Notes:**
- Hides the category from everyone except specified roles
- Syncs permissions for all child channels
- Server owner always has access

#### `/matchups add-game-status`
**Description:** Apply game status tracker to a week (category) or a specific matchup channel. Adds reaction buttons for tracking game outcomes.
**Parameters:**
- `apply_to`: Select "week" to apply to all matchups in a category, or "matchup" to apply to a single channel
- `location`: The category name (if apply_to is "week") or channel name (if apply_to is "matchup")
**Usage:** 
- `/matchups add-game-status apply_to:week location:Week 1` - Adds game status tracker to all matchups in Week 1
- `/matchups add-game-status apply_to:matchup location:oregon-vs-washington` - Adds game status tracker to a specific matchup channel
**Important Notes:**
- Creates a message with reaction buttons: ✅ Completed, 🎲 Fair Sim, 🟥 Force Win Team1, 🟦 Force Win Team2
- If a game status message already exists in the channel, it will be replaced

## Record Commands

### For All Users

#### `/records check-record`
**Description:** Check a team's record.
**Parameters:**
- `team`: The team name
**Usage:** `/records check-record team:Oregon`

#### `/records view-all-records`
**Description:** View all records in the league.
**Usage:** `/records view-all-records` - no parameters needed

### For Commissioners

#### `/records set-record`
**Description:** Manually set a team's record.
**Parameters:**
- `team`: The team name
- `wins`: Number of wins
- `losses`: Number of losses
**Usage:** `/records set-record team:Oregon wins:5 losses:2`

#### `/records clear-team-record`
**Description:** Clear a team's record.
**Parameters:**
- `team`: The team name
**Usage:** `/records clear-team-record team:Oregon`

#### `/records clear-all`
**Description:** Wipe all records.
**Usage:** `/records clear-all` - requires confirmation

## Messaging Commands

### For Commissioners

#### `/message custom`
**Description:** Send a custom message to channels.
**Parameters:**
- `channels`: Mention channels with # (can mention multiple)
- `message`: The message to send
**Usage:** `/message custom channels:#general #announcements message:Hello everyone!`

#### `/message announce-advance`
**Description:** Notify of next advance time.
**Parameters:**
- `channels`: Mention channels with # (can mention multiple)
- `advance_time`: When is the advance? (e.g., "Monday at 8 PM")
**Usage:** `/message announce-advance channels:#general advance_time:Monday at 8 PM`

## Settings Commands

### For Commissioners

#### `/settings set`
**Description:** Configure server settings.
**Parameters:**
- `setting`: The setting to configure (see available settings below)
- `new_value`: The new value for the setting
**Usage:** `/settings set setting:record_tracking_enabled new_value:on`

**Available Settings:**
- `commissioner_roles`: Comma-separated list of role names (e.g., "Commish,Admin")
- `record_tracking_enabled`: Enable/disable record tracking ("on" or "off")
- `attributes_log_channel`: Channel ID for attribute change logs
- `stream_notify_role`: Role to ping for stream announcements
- `stream_watch_channel`: Channel for stream notifications
- `stream_announcements_enabled`: Enable/disable stream features ("on" or "off")
- `league_type`: Default league type ("cfb" or "nfl")

#### `/settings view`
**Description:** See current settings.
**Usage:** `/settings view` - no parameters needed

#### `/settings reset`
**Description:** Remove a setting.
**Parameters:**
- `setting`: The setting to remove
**Usage:** `/settings reset setting:record_tracking_enabled`

#### `/settings clear-all`
**Description:** Wipe all settings.
**Usage:** `/settings clear-all` - requires confirmation

#### `/settings help`
**Description:** Learn how each setting works.
**Usage:** `/settings help` - no parameters needed

## Admin Commands

### For Commissioners

#### `/admin trial`
**Description:** Start 10-day free trial.
**Usage:** `/admin trial` - no parameters needed

#### `/admin purchase`
**Description:** View premium plans.
**Usage:** `/admin purchase` - no parameters needed

#### `/admin activate-annual`
**Description:** Activate annual subscription.
**Parameters:**
- `key`: Your access key
**Usage:** `/admin activate-annual key:YOUR_KEY_HERE`

#### `/admin check-subscription`
**Description:** Check subscription status.
**Usage:** `/admin check-subscription` - no parameters needed

#### `/admin setup-league`
**Description:** Create league structure.
**Usage:** `/admin setup-league` - follow the prompts

#### `/admin guide`
**Description:** Setup walkthrough.
**Usage:** `/admin guide` - no parameters needed

## Ability Lab Command

### For All Users

#### `/ability-lab`
**Description:** Access the interactive Trilo Ability Dashboard.
**Usage:** `/ability-lab` - no parameters needed
**Features:**
- AI Upgrade Assistant for personalized advice
- Visual Ability Tiers (Bronze to Platinum)
- SP Calculator for skill point planning
- Detailed archetype and ability analytics
- Position & archetype filtering

## Help Command

### For All Users

#### `/trilo help`
**Description:** Get help with Trilo Bot features.
**Parameters:**
- `feature`: The feature to get help with (select from dropdown)
- `audience`: Who this help is for (Everyone, Commissioners, or League Members)
**Usage:** `/trilo help feature:attributes audience:all`

**Available Features:**
- Getting Started & Overview
- Admin & Server Management
- Team Management
- Matchup Automation
- Messaging Tools
- Attribute Point System
- Win/Loss Records
- Ability Lab
- Settings

## General Usage Tips

1. **To use a command:** Type `/` and begin typing the command name, or tap the Discord Controller icon to browse available options.

2. **Command Groups:** Many commands are organized into groups (e.g., `/attributes`, `/teams`, `/matchups`). Use autocomplete to see all available subcommands.

3. **Permissions:** Some commands are commissioner-only. If you don't have permission, the bot will let you know.

4. **Subscription Tiers:**
   - **Free Tier:** Ability Lab only
   - **Pro Tier:** All features including Team Management, Matchups, Messaging, Settings, Win/Loss Records, and Attribute Points

5. **Getting Help:** Use `/trilo help` for detailed guidance on any feature, or ask the bot directly by mentioning it!

