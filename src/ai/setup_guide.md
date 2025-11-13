# Trilo Setup & Usage Guide

This comprehensive guide explains how to set up and use Trilo for sports league management on Discord.

---

## 🎯 For First-Time Users

### What is Trilo?

Trilo is an AI-powered Discord bot that automates sports league management. It handles team assignments, matchup creation, win/loss records, attribute points, and more—all within Discord.

**Key Benefits:**
- **95% time savings**: Matchup creation takes 1 minute instead of 3+ hours
- **Zero errors**: AI-powered automation eliminates manual mistakes
- **Discord-native**: No external tools or spreadsheets needed
- **AI conversation**: Ask questions naturally, get instant answers

---

## 👑 Commissioner Setup Guide

### Step 1: Initial Configuration (`/settings`)

Before anything else, configure your league settings:

#### **1.1 Set League Type**
```
/settings set setting:league_type new_value:cfb
```
- Choose `cfb` (College Football) or `nfl`
- This determines team autocompletes and defaults throughout the bot
- **Default**: CFB if not set

#### **1.2 Define Commissioner Roles**
```
/settings set setting:commissioner_roles new_value:Commish,Admin
```
- Comma-separated list of role names with admin access
- Only these roles can use commissioner-only commands
- **Default**: "Commish", "Commissioner", "Commissioners"
- **Note**: Only server administrators can change this setting

#### **1.3 Enable Record Tracking (Optional)**
```
/settings set setting:record_tracking_enabled new_value:on
```
- Turn on if you want automatic win/loss record tracking
- When enabled, records update automatically after games
- Use `off` to disable
- **Default**: Off

#### **1.4 Set Attribute Points Log Channel (Optional)**
```
/settings set setting:attributes_log_channel new_value:#attributes-log
```
- Channel where attribute point changes are logged
- Provides transparency for all point awards, requests, approvals, and denials
- Optional but recommended for competitive leagues

#### **1.5 Configure Stream Announcements (Optional)**

If you want automated stream notifications when league members go live:

**Enable Stream Announcements:**
```
/settings set setting:stream_announcements_enabled new_value:on
```
- Turn on stream detection and notifications
- Bot will watch for Twitch/YouTube streams in messages

**Set Stream Watch Channel:**
```
/settings set setting:stream_watch_channel new_value:#streams
```
- Channel where the bot watches for stream links
- When someone posts a Twitch or YouTube live link, bot detects it

**Set Stream Notify Role:**
```
/settings set setting:stream_notify_role new_value:Streamers
```
- Role that gets pinged when a stream is detected
- Great for alerting the league when someone is streaming games

**How It Works:**
1. Member posts a Twitch/YouTube live stream link in the watch channel
2. Bot automatically detects the stream
3. Bot sends notification mentioning the configured role
4. League members get alerted to watch the stream

**Note:** This is completely optional - only set this up if your league streams games!

#### **1.6 View Your Settings**
```
/settings view
```
- Check all current server settings
- Verify everything is configured correctly

---

### Complete Settings Reference

Here's a quick reference for all available settings:

| Setting | Purpose | Values | Required? |
|---------|---------|--------|-----------|
| `league_type` | Default league for commands | `cfb` or `nfl` | **Recommended** |
| `commissioner_roles` | Roles with admin access | Comma-separated role names | **Recommended** |
| `record_tracking_enabled` | Auto W/L record tracking | `on` or `off` | Optional |
| `attributes_log_channel` | Log attribute point changes | Channel mention or ID | Optional |
| `stream_announcements_enabled` | Stream notification features | `on` or `off` | Optional |
| `stream_watch_channel` | Channel to watch for streams | Channel mention or ID | Optional (if streams enabled) |
| `stream_notify_role` | Role to ping for streams | Role name | Optional (if streams enabled) |

**To change any setting:**
```
/settings set setting:[setting_name] new_value:[value]
```

**To reset a setting to default:**
```
/settings reset setting:[setting_name]
```

**To clear all settings:**
```
/settings clear-all
```

---

### Step 2: Team Assignment (`/teams`)

Assign users to teams so they can participate in matchups:

#### **2.1 Assign a User to a Team**
```
/teams assign-user user:@player team:Oregon Ducks
```
- Mention the user and type/select the team name
- Autocomplete suggests teams based on your league type
- Each user can have one team at a time

#### **2.2 Check Team Ownership**
```
/teams who-has team:Oregon Ducks
```
- See who owns a specific team
- Returns "No user assigned" if team is unassigned

#### **2.3 List All Assignments**
```
/teams list-all
```
- View all team assignments in your server
- Shows who owns which teams
- Helps identify unassigned teams

#### **2.4 Unassign a Team**
```
/teams unassign-team team:Oregon Ducks
```
- Remove a user from a team
- Makes the team available for reassignment

---

### Step 3: Create Matchups (`/matchups`)

The most powerful feature—create weekly matchups in seconds:

#### **3.1 AI-Powered Creation (Recommended)**

**Option A: Use AI Conversation**
1. Upload a screenshot of your matchups
2. Mention the bot: `@Trilo create matchups from this image, name it Week 1, add game status trackers`
3. Review the preview
4. Click "Confirm" to create channels

**Option B: Use Slash Command**
```
/matchups create-from-image category_name:Week 1 image1:[upload] game_status:True
```
- Upload up to 5 images at once
- Bot extracts all team matchups automatically
- 95% accuracy, processes in seconds
- `game_status:True` adds status emojis (✅ played, 🎲 playing, ☑️ ready)
- `roles_allowed:Commissioners` limits channel visibility to specific roles

#### **3.2 Manual Creation (Alternative)**
```
/matchups create category_name:Week 1 league:cfb
```
- Manually enter each matchup one by one
- More time-consuming but gives precise control
- Useful for correcting AI extraction errors

#### **3.3 Add Features to Existing Matchups**

**Add Game Status Trackers**
```
/matchups add-game-status category_name:Week 1
```
- Adds ✅ (played), 🎲 (playing), ☑️ (ready) reactions to all matchup channels
- Users can click to update their game status
- Commissioners can see who's played at a glance

**Tag All Users**
```
/matchups tag-users category_name:Week 1
```
- Mentions all users in their matchup channels
- Sends them a notification
- Great for reminding people to play

**Sync Records from Matchups**
```
/matchups sync-records category_name:Week 1
```
- Updates win/loss records based on channel names
- Looks for "✅" or "❌" in channel names
- Only works if record tracking is enabled

---

### Step 4: Attribute Points System (Optional)

If you want a player progression system with upgrades:

#### **4.1 Give Points to Users**
```
/attributes give user:@player amount:10 reason:Season start bonus
```
- Award attribute points to users
- Logged in the attributes log channel (if configured)
- Users can spend points on upgrades

#### **4.2 View User Points**
```
/attributes my-points
```
- See your own attribute point balance
- Shows available and total points

**Commissioner View**
```
/attributes check-user-points user:@player
```
- Check any user's point balance
- Commissioner-only command

```
/attributes check-all-points
```
- View all users' point balances
- See who has the most points

#### **4.3 User Requests Upgrades**
```
/attributes request attribute:speed amount:3 player:Bo Nix player_team:Oregon Ducks
```
- Users spend points to request upgrades
- Goes to pending status for commissioner review
- Points are deducted from available balance

#### **4.4 Commissioner Reviews Requests**

**View Pending Requests**
```
/attributes pending-requests
```
- See all requests awaiting approval
- Shows attribute, amount, player, and requester

**Approve a Request**
```
/attributes approve request_id:123
```
- Approve an upgrade request
- Points are permanently spent
- Logged in attributes log channel

**Deny a Request**
```
/attributes deny request_id:123 reason:Not enough justification
```
- Deny an upgrade request
- Points are refunded to user
- Reason is sent to the requester

**View Request History**
```
/attributes request-history user:@player
```
- See all approved/denied requests for a user
- Track player progression over time

---

### Step 5: Records Management (If Enabled)

If you enabled record tracking in Step 1:

#### **5.1 Set Team Record Manually**
```
/records set team:Oregon Ducks wins:8 losses:2
```
- Manually set or adjust a team's record
- Useful for correcting errors or setting initial records

#### **5.2 Check Team Record**
```
/records check team:Oregon Ducks
```
- View a team's current record
- Shows wins and losses

#### **5.3 View All Records**
```
/records view-all
```
- See standings for all teams
- Sorted by win percentage
- Great for league standings announcements

---

### Step 6: Messaging & Announcements (`/message`)

Communicate with your league efficiently:

#### **6.1 Announce Advance**
```
/message announce-advance week:2 advance_time:Sunday 8pm channels:#general,#announcements
```
- Notify league when to advance to next week
- Mention in multiple channels at once
- Includes week number and advance time
- Optional custom message

#### **6.2 Send Custom Message**
```
/message custom channels:#general message:Don't forget to play your games!
```
- Send announcements to multiple channels
- Useful for reminders, rule updates, etc.

---

## 🎮 Player Usage Guide

### For League Members (Non-Commissioners)

#### **Check Your Team**
```
/teams my-team
```
- See which team you're assigned to
- Returns "not assigned" if you don't have a team yet

#### **Check Your Points**
```
/attributes my-points
```
- View your available attribute points
- See how many you can spend on upgrades

#### **Request Upgrades**
```
/attributes request attribute:speed amount:3 player:Bo Nix player_team:Oregon Ducks
```
- Spend points to upgrade your players
- Commissioner will approve or deny
- Check `/attributes pending-requests` to see status

#### **View Your Request History**
```
/attributes request-history
```
- See all your past upgrade requests
- Shows approved and denied requests

#### **Check Matchups**
Ask Trilo: `@Trilo what are this week's matchups?`
- AI will show you all current matchups
- No need to search through channels

---

## 🤖 AI Conversation Features

Trilo understands natural language! You can ask questions instead of using slash commands:

### **Get Information**
- "Show me my points"
- "What's my team?"
- "Who has the Oregon Ducks?"
- "What are this week's matchups?"
- "Show all records"
- "When is advance?"

### **Get Help**
- "How do I use you?"
- "How do I spend my points?"
- "What command shows matchups?"
- "How do I create matchups?"

### **Summarize Conversations**
- "Summarize the last 20 messages"
- "What did we talk about today?"
- "Recap the last 2 hours"
- "TLDR"

### **Execute Commands (Commissioners)**
- "Create matchups from this image, name it Week 1, add game status"
- "Delete Week 0 matchups"
- "Tag users in Week 1"
- "Announce advance for Week 2 at Sunday 8pm"

### **Fun Predictions**
- "Who will win, BYU or Oregon?"
- The bot will pick a winner casually (no real stats, just for fun!)

---

## 🛠️ Advanced Features

### **Matchup Management**

#### **Delete Matchup Categories**
```
/matchups delete
```
- Select categories to delete from dropdown
- Preview shows what will be deleted
- Confirm to remove categories and all channels

Via AI: `@Trilo delete Week 0 matchups`

#### **Make Matchups Public/Private**
```
/matchups make-public category_name:Week 1
```
```
/matchups make-private category_name:Week 1 roles_allowed:Commissioners
```
- Control who can see matchup channels
- Public: Everyone can see
- Private: Only specified roles

#### **List Matchups in Category**
```
/matchups list category_name:Week 1
```
- See all matchups in a category
- Shows team vs team and user assignments
- Displays game status if enabled

---

## 📋 Best Practices

### **For Commissioners**

1. **Set up settings first** - Configure league type, commissioners, and record tracking before anything else
2. **Assign teams early** - Get all users assigned to teams before creating matchups
3. **Use AI for matchups** - Upload screenshots instead of manual entry (95% accuracy, 99% time savings)
4. **Enable game status** - Add status trackers so you know who's played without asking
5. **Tag users weekly** - Send notifications at start of each week to remind people to play
6. **Check logs regularly** - Review attribute log channel to ensure fair play

### **For Players**

1. **Check your assignment** - Use `/teams my-team` to see your team
2. **Track your points** - Use `/attributes my-points` regularly
3. **Request upgrades thoughtfully** - Commissioners can deny vague requests
4. **Update game status** - Click reactions in matchup channels to show you've played
5. **Ask Trilo questions** - Use natural language instead of memorizing commands

---

## 🔐 Privacy & Security

### **What Trilo Logs**
- Command usage (anonymized server/user IDs)
- Execution times for performance monitoring
- Error tracking for bug fixes

### **What Trilo NEVER Logs**
- Message content (except when you directly mention the bot)
- Personal information (names, emails, etc.)
- Voice chat data
- Private DM contents (unless you DM the bot directly)

### **Data Protection**
- All IDs are hashed (one-way encryption)
- No data is sold or shared with third parties
- Logs are automatically cleaned up after 30 days
- GDPR-compliant data handling

---

## ❓ Common Questions

### "Do I need to use all features?"
No! Use only what you need. Many leagues just use team assignments and matchups. Attribute points and record tracking are optional.

### "Can I change settings later?"
Yes! Use `/settings set` anytime to update settings. Changes take effect immediately.

### "What if AI gets matchups wrong?"
The AI has 95% accuracy, but you can manually edit or delete/recreate if needed. You can also use `/matchups create` for manual entry.

### "How do I reset everything?"
Use `/settings clear-all` to remove all settings. Use `/matchups delete` to remove matchup categories. Team assignments can be unassigned individually.

### "Can players see each other's points?"
No, unless you use `/attributes check-all-points` (commissioner only). Players can only see their own points with `/attributes my-points`.

### "What happens if I run out of subscription?"
Free tier allows basic features. Core and Pro tiers unlock advanced automation and AI features. Active subscriptions are required for premium commands.

---

## 🆘 Getting Help

### **Ask Trilo Directly**
`@Trilo how do I [whatever you need help with]?`

The AI understands natural language and can explain any feature!

### **Use Built-in Help**
```
/settings help
```
- Explains all settings in detail

### **Contact Support**
- Join the Trilo support Discord (coming soon)
- Report bugs or request features

---

## 🎉 Quick Start Checklist

For commissioners setting up a new league:

- [ ] Configure league type (`/settings set setting:league_type`)
- [ ] Set commissioner roles (`/settings set setting:commissioner_roles`)
- [ ] Enable record tracking if desired (`/settings set setting:record_tracking_enabled`)
- [ ] Set up attributes log channel (optional: `/settings set setting:attributes_log_channel`)
- [ ] Configure stream announcements if your league streams (optional: `/settings set setting:stream_announcements_enabled`)
- [ ] Assign all users to teams (`/teams assign-user`)
- [ ] Create first week matchups (AI or manual)
- [ ] Add game status trackers (`/matchups add-game-status`)
- [ ] Tag users to notify them (`/matchups tag-users`)
- [ ] Give initial attribute points if using that system (`/attributes give`)
- [ ] Announce advance schedule (`/message announce-advance`)

**You're ready to go!** 🚀

---

*Last updated: November 2024*

