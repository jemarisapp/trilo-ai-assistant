import sqlite3
import os


# Set database file name and path
BASE_DIR = os.path.dirname(__file__)
DB_PATH = os.path.join(BASE_DIR, "bot_data_archetypes.db")

# Create and connect to the database
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Updated stat-based insert logic
def insert_dual_stat_tiers(cursor, ability_name, stats_by_tier):
    default_costs = {"Bronze": 2, "Silver": 4, "Gold": 6, "Platinum": 8}

    for tier, stats in stats_by_tier.items():
        stat_1 = stats[0] if len(stats) > 0 else None

        # NEW LOGIC: Detect if stat_2 is provided or if it's actually the SP cost
        stat_2 = None
        sp_cost = default_costs.get(tier, 2)

        if len(stats) == 2:
            if isinstance(stats[1], tuple):
                stat_2 = stats[1]
            else:
                sp_cost = stats[1]
        elif len(stats) >= 3:
            stat_2 = stats[1]
            sp_cost = stats[2]

        cursor.execute("""
            INSERT INTO ability_tiers (
                ability_id, tier, stat_1_name, stat_1_value,
                stat_2_name, stat_2_value, sp_cost
            )
            SELECT id, ?, ?, ?, ?, ?, ? FROM abilities WHERE name = ?
        """, (
            tier,
            stat_1[0], stat_1[1],
            stat_2[0] if stat_2 else None,
            stat_2[1] if stat_2 else None,
            sp_cost,
            ability_name
        ))

def insert_archetype_specific_tiers(cursor, archetype_name, ability_name, stats_by_tier):
    default_costs = {"Bronze": 2, "Silver": 4, "Gold": 6, "Platinum": 8}

    for tier, stats in stats_by_tier.items():
        stat_1 = stats[0] if len(stats) > 0 else None
        stat_2 = None
        sp_cost = default_costs.get(tier, 2)

        if len(stats) == 2:
            if isinstance(stats[1], tuple):
                stat_2 = stats[1]
            else:
                sp_cost = stats[1]
        elif len(stats) >= 3:
            stat_2 = stats[1]
            sp_cost = stats[2]

        cursor.execute("""
            INSERT INTO ability_tiers (
                ability_id, archetype_id, tier,
                stat_1_name, stat_1_value,
                stat_2_name, stat_2_value,
                sp_cost
            )
            SELECT ab.id, ar.id, ?, ?, ?, ?, ?, ?
            FROM abilities ab, archetypes ar
            WHERE ab.name = ? AND ar.name = ?
        """, (
            tier,
            stat_1[0], stat_1[1],
            stat_2[0] if stat_2 else None,
            stat_2[1] if stat_2 else None,
            sp_cost,
            ability_name, archetype_name
        ))


cursor.executescript("""
DROP TABLE IF EXISTS positions;
DROP TABLE IF EXISTS archetypes;
DROP TABLE IF EXISTS abilities;
DROP TABLE IF EXISTS ability_tiers;
DROP TABLE IF EXISTS archetype_abilities;

CREATE TABLE positions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL
);

CREATE TABLE archetypes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    position_id INTEGER NOT NULL,
    FOREIGN KEY (position_id) REFERENCES positions(id)
);

CREATE TABLE abilities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL
);

CREATE TABLE ability_tiers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ability_id INTEGER NOT NULL,
    archetype_id INTEGER NOT NULL,  -- ✅ NEW
    tier TEXT NOT NULL,
    stat_1_name TEXT NOT NULL,
    stat_1_value INTEGER NOT NULL,
    stat_2_name TEXT,
    stat_2_value INTEGER,
    sp_cost INTEGER NOT NULL,
    FOREIGN KEY (ability_id) REFERENCES abilities(id),
    FOREIGN KEY (archetype_id) REFERENCES archetypes(id)
);


CREATE TABLE archetype_abilities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    archetype_id INTEGER NOT NULL,
    ability_id INTEGER NOT NULL,
    ability_order INTEGER NOT NULL,
    FOREIGN KEY (archetype_id) REFERENCES archetypes(id),
    FOREIGN KEY (ability_id) REFERENCES abilities(id)
);

CREATE TABLE ability_descriptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ability_id INTEGER NOT NULL,
    tier TEXT NOT NULL CHECK (tier IN ('Bronze', 'Silver', 'Gold', 'Platinum')),
    description TEXT NOT NULL,
    FOREIGN KEY (ability_id) REFERENCES abilities(id),
    UNIQUE (ability_id, tier)
);


""")

# Insert positions
for pos in [
    "QB", "HB", "FB", "WR", "TE", "OL", "DL", "LB", "CB", "S", "K/P"
]:
    cursor.execute("INSERT OR IGNORE INTO positions (name) VALUES (?)", (pos,))

# Archetypes
archetypes = {
    "QB": [
        "Backfield Creator",
        "Dual Threat",
        "Pocket Passer",
        "Pure Runner"
    ],

    "HB": [
        "Backfield Threat",
        "Contact Seeker",
        "East/West Playmaker",
        "Elusive Bruiser",
        "North/South Receiver",
        "North/South Blocker"
    ],

    "FB": [
        "Blocking",
        "Utility"
    ],
    
    "WR": [
        "Contested Specialist",
        "Elusive Route Runner",
        "Gadget",
        "Gritty Possession WR",
        "Physical Route Runner WR",
        "Route Artist",
        "Speedster"
    ],
    
     "TE": [
        "Gritty Possession TE",
        "Physical Route Runner TE",
        "Possession",
        "Pure Blocker",
        "Vertical Threat"
    ],
    "OL": [
        "Agile",
        "Pass Protector",
        "Raw Strength",
        "Well Rounded"
    ],
    "DL": [
        "Edge Setter",
        "Gap Specialist",
        "Physical Freak",
        "Power Rusher",
        "Speed Rusher"
    ],
    "LB": [
        "Lurker",
        "Signal Caller",
        "Thumper"
    ],
    "CB": [
        "Boundary",
        "Bump and Run",
        "Field",
        "Zone"
    ],
    "S": [
        "Box Specialist",
        "Coverage Specialist",
        "Hybrid"
    ],
    "K/P": [
        "Accurate",
        "Power"
    ]

}

for position, types in archetypes.items():
    for archetype in types:
        cursor.execute("""
            INSERT INTO archetypes (name, position_id)
            SELECT ?, id FROM positions WHERE name = ?
        """, (archetype, position))



# Stat tiers per ability
ability_stats = {
    "Mobile Deadeye": {
        "Bronze": [("Attribute", 0), 1],
        "Silver": [("Attribute", 0), 1],
        "Gold": [("Attribute", 0), 1],
        "Platinum": [("Attribute", 0), 1],
    },
    "House Call": {
        "Bronze": [("Attribute", 0), 1],
        "Silver": [("Attribute", 0), 1],
        "Gold": [("Attribute", 0), 1],
        "Platinum": [("Attribute", 0), 1],
    },
    "360": {
        "Bronze": [("Attribute", 0), 1],
        "Silver": [("Attribute", 0), 1],
        "Gold": [("Attribute", 0), 1],
        "Platinum": [("Attribute", 0), 1],
    },
    "Headfirst": {
        "Bronze": [("Attribute", 0), 1],
        "Silver": [("Attribute", 0), 1],
        "Gold": [("Attribute", 0), 1],
        "Platinum": [("Attribute", 0), 1],
    },
    "Step Up": {
        "Bronze": [("Attribute", 0), 1],
        "Silver": [("Attribute", 0), 1],
        "Gold": [("Attribute", 0), 1],
        "Platinum": [("Attribute", 0), 1],
    },
    "Sleight Of Hand": {
        "Bronze": [("Attribute", 0), 1],
        "Silver": [("Attribute", 0), 1],
        "Gold": [("Attribute", 0), 1],
        "Platinum": [("Attribute", 0), 1],
    },
    "Magician": {
        "Bronze": [("Attribute", 0), 1],
        "Silver": [("Attribute", 0), 1],
        "Gold": [("Attribute", 0), 1],
        "Platinum": [("Attribute", 0), 1],
    },
    "Off Platform": {
        "Bronze": [("Attribute", 0), ("Attribute", 0), 1],
        "Silver": [("Attribute", 0), ("Attribute", 0), 1],
        "Gold": [("Attribute", 0), ("Attribute", 0), 1],
        "Platinum": [("Attribute", 0), ("Attribute", 0), 1],
    },
    "Safety Valve": {
        "Bronze": [("Attribute", 0), 1],
        "Silver": [("Attribute", 0), 1],
        "Gold": [("Attribute", 0), 1],
        "Platinum": [("Attribute", 0), 1],
    },
    "Pocket Shield": {
        "Bronze": [("Attribute", 0), 1],
        "Silver": [("Attribute", 0), 1],
        "Gold": [("Attribute", 0), 1],
        "Platinum": [("Attribute", 0), 1],
    },
    "Extender": {
        "Bronze": [("Attribute", 0), 1],
        "Silver": [("Attribute", 0), 1],
        "Gold": [("Attribute", 0), 1],
        "Platinum": [("Attribute", 0), 1],
    },
    "Knockout": {
        "Bronze": [("Attribute", 0), 1],
        "Silver": [("Attribute", 0), 1],
        "Gold": [("Attribute", 0), 1],
        "Platinum": [("Attribute", 0), 1],
    },
    "Duress": {
        "Bronze": [("Attribute", 0), 1],
        "Silver": [("Attribute", 0), 1],
        "Gold": [("Attribute", 0), 1],
        "Platinum": [("Attribute", 0), 1],
    },
    "Hammer": {
        "Bronze": [("Attribute", 0), 1],
        "Silver": [("Attribute", 0), 1],
        "Gold": [("Attribute", 0), 1],
        "Platinum": [("Attribute", 0), 1],
    },
    "Wrap Up": {
        "Bronze": [("Attribute", 0), 1],
        "Silver": [("Attribute", 0), 1],
        "Gold": [("Attribute", 0), 1],
        "Platinum": [("Attribute", 0), 1],
    },
    "Shifty": {
        "Bronze": [("Attribute", 0), ("Attribute", 0), 1],
        "Silver": [("Attribute", 0), ("Attribute", 0), 1],
        "Gold": [("Attribute", 0), ("Attribute", 0), 1],
        "Platinum": [("Attribute", 0), ("Attribute", 0), 1],
    },
    "Side Step": {
        "Bronze": [("Attribute", 0), 1],
        "Silver": [("Attribute", 0), 1],
        "Gold": [("Attribute", 0), 1],
        "Platinum": [("Attribute", 0), 1],
    },
    "Lay Out": {
        "Bronze": [("Attribute", 0), 1],
        "Silver": [("Attribute", 0), 1],
        "Gold": [("Attribute", 0), 1],
        "Platinum": [("Attribute", 0), 1],
    },
    "Take Down": {
        "Bronze": [("Attribute", 0), 1],
        "Silver": [("Attribute", 0), 1],
        "Gold": [("Attribute", 0), 1],
        "Platinum": [("Attribute", 0), 1],
    },
    "50/50": {
        "Bronze": [("Attribute", 0), 1],
        "Silver": [("Attribute", 0), 1],
        "Gold": [("Attribute", 0), 1],
        "Platinum": [("Attribute", 0), 1],
    },
    "Balanced": {
        "Bronze": [("Attribute", 0), 1],
        "Silver": [("Attribute", 0), 1],
        "Gold": [("Attribute", 0), 1],
        "Platinum": [("Attribute", 0), 1],
    },
    "Blow Up": {
        "Bronze": [("Attribute", 0), 1],
        "Silver": [("Attribute", 0), 1],
        "Gold": [("Attribute", 0), 1],
        "Platinum": [("Attribute", 0), 1],
    },
    "Bouncer": {
        "Bronze": [("Attribute", 0), 1],
        "Silver": [("Attribute", 0), 1],
        "Gold": [("Attribute", 0), 1],
        "Platinum": [("Attribute", 0), 1],
    },
    "Jammer": {
        "Bronze": [("Attribute", 0), 1],
        "Silver": [("Attribute", 0), 1],
        "Gold": [("Attribute", 0), 1],
        "Platinum": [("Attribute", 0), 1],
    },
    "Blanket Coverage": {
        "Bronze": [("Attribute", 0), 1],
        "Silver": [("Attribute", 0), 1],
        "Gold": [("Attribute", 0), 1],
        "Platinum": [("Attribute", 0), 1],
    },
    "Mobile Resistance": {
        "Bronze": [("Attribute", 0), 1],
        "Silver": [("Attribute", 0), 1],
        "Gold": [("Attribute", 0), 1],
        "Platinum": [("Attribute", 0), 1],
    },
    "Recoup": {
        "Bronze": [("Attribute", 0), 1],
        "Silver": [("Attribute", 0), 1],
        "Gold": [("Attribute", 0), 1],
        "Platinum": [("Attribute", 0), 1],
    },
    "Resistance": {
        "Bronze": [("Attribute", 0), 1],
        "Silver": [("Attribute", 0), 1],
        "Gold": [("Attribute", 0), 1],
        "Platinum": [("Attribute", 0), 1],
    },
    "Dot!": {
        "Bronze": [("Attribute", 0), 1],
        "Silver": [("Attribute", 0), 1],
        "Gold": [("Attribute", 0), 1],
        "Platinum": [("Attribute", 0), 1],
    },
    "Pull Down": {
        "Bronze": [("Attribute", 0), 1],
        "Silver": [("Attribute", 0), 1],
        "Gold": [("Attribute", 0), 1],
        "Platinum": [("Attribute", 0), 1],
    },
    "Option King": {
        "Bronze": [("Attribute", 0), 1],
        "Silver": [("Attribute", 0), 1],
        "Gold": [("Attribute", 0), 1],
        "Platinum": [("Attribute", 0), 1],
    },
    "Workhorse": {
        "Bronze": [("Attribute", 0), 1],
        "Silver": [("Attribute", 0), 1],
        "Gold": [("Attribute", 0), 1],
        "Platinum": [("Attribute", 0), 1],
    },
    "Downhill": {
        "Bronze": [("Break Tackle", 84), 4],
        "Silver": [("Break Tackle", 87), 4],
        "Gold": [("Break Tackle", 92), 8],
        "Platinum": [("Break Tackle", 94), 10],
    },
    "Sure Hands": {
        "Bronze": [("Attribute", 0), 1],
        "Silver": [("Attribute", 0), 1],
        "Gold": [("Attribute", 0), 1],
        "Platinum": [("Attribute", 0), 1],
    },
    "Cutter": {
        "Bronze": [("Attribute", 0), 1],
        "Silver": [("Attribute", 0), 1],
        "Gold": [("Attribute", 0), 1],
        "Platinum": [("Attribute", 0), 1],
    },
    "Double Dip": {
        "Bronze": [("Attribute", 0), 1],
        "Silver": [("Attribute", 0), 1],
        "Gold": [("Attribute", 0), 1],
        "Platinum": [("Attribute", 0), 1],
    },
    "Press Pro": {
        "Bronze": [("Attribute", 0), 1],
        "Silver": [("Attribute", 0), 1],
        "Gold": [("Attribute", 0), 1],
        "Platinum": [("Attribute", 0), 1],
    },
    "Quick Drop": {
        "Bronze": [("Attribute", 0), 1],
        "Silver": [("Attribute", 0), 1],
        "Gold": [("Attribute", 0), 1],
        "Platinum": [("Attribute", 0), 1],
    },
    "Option Shield": {
        "Bronze": [("Attribute", 0), 1],
        "Silver": [("Attribute", 0), 1],
        "Gold": [("Attribute", 0), 1],
        "Platinum": [("Attribute", 0), 1],
    },
    "Inside Shield": {
        "Bronze": [("Attribute", 0), 1],
        "Silver": [("Attribute", 0), 1],
        "Gold": [("Attribute", 0), 1],
        "Platinum": [("Attribute", 0), 1],
    },
    "Screen Enforcer": {
        "Bronze": [("Attribute", 0), 1],
        "Silver": [("Attribute", 0), 1],
        "Gold": [("Attribute", 0), 1],
        "Platinum": [("Attribute", 0), 1],
    },
    "PA Shield": {
        "Bronze": [("Attribute", 0), 1],
        "Silver": [("Attribute", 0), 1],
        "Gold": [("Attribute", 0), 1],
        "Platinum": [("Attribute", 0), 1],
    },
    "Second Level": {
        "Bronze": [("Attribute", 0), 1],
        "Silver": [("Attribute", 0), 1],
        "Gold": [("Attribute", 0), 1],
        "Platinum": [("Attribute", 0), 1],
    },
    "Outside Shield": {
        "Bronze": [("Attribute", 0), 1],
        "Silver": [("Attribute", 0), 1],
        "Gold": [("Attribute", 0), 1],
        "Platinum": [("Attribute", 0), 1],
    },
    "Inside Disruptor": {
        "Bronze": [("Attribute", 0), 1],
        "Silver": [("Attribute", 0), 1],
        "Gold": [("Attribute", 0), 1],
        "Platinum": [("Attribute", 0), 1],
    },
    "Outside Disruptor": {
        "Bronze": [("Attribute", 0), 1],
        "Silver": [("Attribute", 0), 1],
        "Gold": [("Attribute", 0), 1],
        "Platinum": [("Attribute", 0), 1],
    },
    "Option Disruptor": {
        "Bronze": [("Attribute", 0), 1],
        "Silver": [("Attribute", 0), 1],
        "Gold": [("Attribute", 0), 1],
        "Platinum": [("Attribute", 0), 1],
    },
    "Pocket Disruptor": {
        "Bronze": [("Attribute", 0), 1],
        "Silver": [("Attribute", 0), 1],
        "Gold": [("Attribute", 0), 1],
        "Platinum": [("Attribute", 0), 1],
    },
    "Strong Grip": {
        "Bronze": [("Attribute", 0), 1],
        "Silver": [("Attribute", 0), 1],
        "Gold": [("Attribute", 0), 1],
        "Platinum": [("Attribute", 0), 1],
    },
    "Ground N Pound": {
        "Bronze": [("Attribute", 0), 1],
        "Silver": [("Attribute", 0), 1],
        "Gold": [("Attribute", 0), 1],
        "Platinum": [("Attribute", 0), 1],
    },
    "Grip Breaker": {
        "Bronze": [("Attribute", 0), 1],
        "Silver": [("Attribute", 0), 1],
        "Gold": [("Attribute", 0), 1],
        "Platinum": [("Attribute", 0), 1],
    },
    "Wear Down": {
        "Bronze": [("Attribute", 0), 1],
        "Silver": [("Attribute", 0), 1],
        "Gold": [("Attribute", 0), 1],
        "Platinum": [("Attribute", 0), 1],
    },
    "Aftershock": {
        "Bronze": [("Attribute", 0), 1],
        "Silver": [("Attribute", 0), 1],
        "Gold": [("Attribute", 0), 1],
        "Platinum": [("Attribute", 0), 1],
    },
    "Ball Hawk": {
        "Bronze": [("Attribute", 0), 1],
        "Silver": [("Attribute", 0), 1],
        "Gold": [("Attribute", 0), 1],
        "Platinum": [("Attribute", 0), 1],
    },
    "Robber": {
        "Bronze": [("Attribute", 0), 1],
        "Silver": [("Attribute", 0), 1],
        "Gold": [("Attribute", 0), 1],
        "Platinum": [("Attribute", 0), 1],
    },
    "Takeoff": {
        "Bronze": [("Attribute", 0), 1],
        "Silver": [("Attribute", 0), 1],
        "Gold": [("Attribute", 0), 1],
        "Platinum": [("Attribute", 0), 1],
    },
    "Quick Jump": {
        "Bronze": [("Attribute", 0), 1],
        "Silver": [("Attribute", 0), 1],
        "Gold": [("Attribute", 0), 1],
        "Platinum": [("Attribute", 0), 1],
    },
    "Quick Step": {
        "Bronze": [("Attribute", 0), 1],
        "Silver": [("Attribute", 0), 1],
        "Gold": [("Attribute", 0), 1],
        "Platinum": [("Attribute", 0), 1],
    },
    "Deep Range": {
        "Bronze": [("Attribute", 0), 0],
        "Silver": [("Attribute", 0), 0],
        "Gold": [("Attribute", 0), 0],
        "Platinum": [("Attribute", 0), 0],
    },
    "Mega Leg": {
        "Bronze": [("Attribute", 0), 1],
        "Silver": [("Attribute", 0), 1],
        "Gold": [("Attribute", 0), 1],
        "Platinum": [("Attribute", 0), 1],
    },
    "Coffin Corner": {
        "Bronze": [("Attribute", 0), 1],
        "Silver": [("Attribute", 0), 1],
        "Gold": [("Attribute", 0), 1],
        "Platinum": [("Attribute", 0), 1],
    },
    "Field Flip": {
        "Bronze": [("Attribute", 0), 1],
        "Silver": [("Attribute", 0), 1],
        "Gold": [("Attribute", 0), 1],
        "Platinum": [("Attribute", 0), 1],
    },
    "Chip Shot": {
        "Bronze": [("Attribute", 0), 1],
        "Silver": [("Attribute", 0), 1],
        "Gold": [("Attribute", 0), 1],
        "Platinum": [("Attribute", 0), 1],
    },
    "Battering Ram": {
        "Bronze": [("Attribute", 0), 1],
        "Silver": [("Attribute", 0), 1],
        "Gold": [("Attribute", 0), 1],
        "Platinum": [("Attribute", 0), 1],
    },
    "Ball Security": {
        "Bronze": [("Attribute", 0), 1],
        "Silver": [("Attribute", 0), 1],
        "Gold": [("Attribute", 0), 1],
        "Platinum": [("Attribute", 0), 1],
    },
    "On Time": {
        "Bronze": [("Attribute", 0), 1],
        "Silver": [("Attribute", 0), 1],
        "Gold": [("Attribute", 0), 1],
        "Platinum": [("Attribute", 0), 1],
    },
    "Instinct": {
        "Bronze": [("Attribute", 0), 1],
        "Silver": [("Attribute", 0), 1],
        "Gold": [("Attribute", 0), 1],
        "Platinum": [("Attribute", 0), 1],
    },
    "Arm Bar": {
        "Bronze": [("Attribute", 0), 1],
        "Silver": [("Attribute", 0), 1],
        "Gold": [("Attribute", 0), 1],
        "Platinum": [("Attribute", 0), 1],
    },
    "Sidekick": {
        "Bronze": [("Attribute", 0), 1],
        "Silver": [("Attribute", 0), 1],
        "Gold": [("Attribute", 0), 1],
        "Platinum": [("Attribute", 0), 1],
    },
}

archetype_ability_tiers = {

# ───────────── QB ─────────────

    "Backfield Creator": {
        "Off Platform": {
            "Bronze": [("THP", 90), ("SAC", 82), 3],
            "Silver": [("THP", 92), ("SAC", 83), 3],
            "Gold": [("THP", 94), ("SAC", 84), 7],
            "Platinum": [("THP", 96), ("SAC", 86), 9],
        },
        "Pull Down": {
            "Bronze": [("CAR", 72), 2],
            "Silver": [("CAR", 75), 2],
            "Gold": [("CAR", 79), 6],
            "Platinum": [("CAR", 83), 8],
        },
        "On Time": {
            "Bronze": [("SAC", 89), 4],
            "Silver": [("SAC", 90), 4],
            "Gold": [("SAC", 92), 8],
            "Platinum": [("SAC", 94), 10],
        },
        "Sleight Of Hand": {
            "Bronze": [("PAC", 84), 3],
            "Silver": [("PAC", 86), 3],
            "Gold": [("PAC", 90), 7],
            "Platinum": [("PAC", 95), 9],
        },
        "Mobile Deadeye": {
            "Bronze": [("TOR", 86), 2],
            "Silver": [("TOR", 88), 2],
            "Gold": [("TOR", 92), 6],
            "Platinum": [("TOR", 94), 8],
        },
    },

    "Dual Threat": {
        "Downhill": {
            "Bronze": [("BTK", 84), 4],
            "Silver": [("BTK", 87), 4],
            "Gold": [("BTK", 92), 8],
            "Platinum": [("BTK", 94), 10],
        },
        "Extender": {
            "Bronze": [("BSK", 83), 3],
            "Silver": [("BSK", 86), 3],
            "Gold": [("BSK", 89), 7],
            "Platinum": [("BSK", 93), 9],
        },
        "Option King": {
            "Bronze": [("BTK", 80), 3],
            "Silver": [("BTK", 83), 3],
            "Gold": [("BTK", 86), 7],
            "Platinum": [("BTK", 90), 9],
        },
        "Dot!": {
            "Bronze": [("DAC", 85), 3],
            "Silver": [("DAC", 87), 3],
            "Gold": [("DAC", 90), 7],
            "Platinum": [("DAC", 93), 9],
        },
        "Mobile Resistance": {
            "Bronze": [("PRU", 82), 2],
            "Silver": [("PRU", 83), 2],
            "Gold": [("PRU", 84), 6],
            "Platinum": [("PRU", 86), 8],
        },
    },

    "Pocket Passer": {
        "Resistance": {
            "Bronze": [("PRU", 83), 3],
            "Silver": [("PRU", 87), 3],
            "Gold": [("PRU", 91), 7],
            "Platinum": [("PRU", 93), 9],
        },
        "Step Up": {
            "Bronze": [("MAC", 86), 3],
            "Silver": [("MAC", 87), 3],
            "Gold": [("MAC", 90), 7],
            "Platinum": [("MAC", 93), 9],
        },
        "Dot!": {
            "Bronze": [("DAC", 85), 3],
            "Silver": [("DAC", 87), 3],
            "Gold": [("DAC", 90), 7],
            "Platinum": [("DAC", 93), 9],
        },
        "Pull Down": {
            "Bronze": [("CAR", 72), 4],
            "Silver": [("CAR", 75), 4],
            "Gold": [("CAR", 79), 8],
            "Platinum": [("CAR", 83), 10],
        },
        "On Time": {
            "Bronze": [("SAC", 89), 2],
            "Silver": [("SAC", 90), 2],
            "Gold": [("SAC", 92), 6],
            "Platinum": [("SAC", 94), 8],
        },
    },

    "Pure Runner": {
        "Magician": {
            "Bronze": [("SPD", 84), 2], # ESTIMATED
            "Silver": [("SPD", 86), 2], # ESTIMATED
            "Gold": [("SPD", 91), 6], # ESTIMATED
            "Platinum": [("SPD", 92), 8], # ESTIMATED
        },
        "Shifty": {
            "Bronze": [("COD", 94), ("ACC", 90), 4], # ESTIMATED
            "Silver": [("COD", 95), ("ACC", 91), 4], # ESTIMATED
            "Gold": [("COD", 96), ("ACC", 93), 8], # ESTIMATED
            "Platinum": [("COD", 97), ("ACC", 96), 10], # ESTIMATED
        },
        "Option King": {
            "Bronze": [("BTK", 80), 3],
            "Silver": [("BTK", 83), 3],
            "Gold": [("BTK", 86), 7],
            "Platinum": [("BTK", 90), 9],
        },
        "Side Step": {
            "Bronze": [("JUKE", 87), 3], # ESTIMATED
            "Silver": [("JUKE", 88), 3], # ESTIMATED
            "Gold": [("JUKE", 91), 7], # ESTIMATED
            "Platinum": [("JUKE", 93), 9], # ESTIMATED
        },
        "Workhorse": {
            "Bronze": [("TGH", 90), 2], # ESTIMATED
            "Silver": [("TGH", 92), 2], # ESTIMATED
            "Gold": [("TGH", 94), 6], # ESTIMATED
            "Platinum": [("TGH", 96), 8], # ESTIMATED
        },
    },

    
# ───────────── HB ─────────────

    "Backfield Threat": {
        "360": {
            "Bronze": [("SPM", 85), 3],
            "Silver": [("SPM", 86), 3],
            "Gold": [("SPM", 87), 7],
            "Platinum": [("SPM", 89), 9],
        },
        "Safety Valve": {
            "Bronze": [("CTH", 73), 2],
            "Silver": [("CTH", 76), 2],
            "Gold": [("CTH", 80), 6],
            "Platinum": [("CTH", 85), 8],
        },
        "Takeoff": {
            "Bronze": [("ACC", 95), 3],
            "Silver": [("ACC", 96), 3],
            "Gold": [("ACC", 98), 7],
            "Platinum": [("ACC", 98), 9],
        },
        "Side Step": {
            "Bronze": [("JUKE", 87), 2],
            "Silver": [("JUKE", 88), 2],
            "Gold": [("JUKE", 91), 6],
            "Platinum": [("JUKE", 93), 8],
        },
        "Recoup": {
            "Bronze": [("STM", 95), 4],
            "Silver": [("STM", 96), 4],
            "Gold": [("STM", 97), 8],
            "Platinum": [("STM", 98), 10],
        },
    },


    "Contact Seeker": {
        "Downhill": {
            "Bronze": [("BTK", 84), 3],
            "Silver": [("BTK", 87), 3],
            "Gold": [("BTK", 92), 7],
            "Platinum": [("BTK", 94), 9],
        },
        "Workhorse": {
            "Bronze": [("TGH", 90), 2],
            "Silver": [("TGH", 92), 2],
            "Gold": [("TGH", 94), 6],
            "Platinum": [("TGH", 96), 8],
        },
        "Battering Ram": {
            "Bronze": [("TGH", 90), ("AWR", 88), 2],
            "Silver": [("TGH", 91), ("AWR", 89), 2],
            "Gold": [("TGH", 92), ("AWR", 90), 6],
            "Platinum": [("TGH", 94), ("AWR", 91), 8],
        },
        "Ball Security": {
            "Bronze": [("CAR", 90), 4],
            "Silver": [("CAR", 91), 4],
            "Gold": [("CAR", 92), 8],
            "Platinum": [("CAR", 94), 10],
        },
        "Balanced": {
            "Bronze": [("STR", 83), 3],
            "Silver": [("STR", 85), 3],
            "Gold": [("STR", 87), 7],
            "Platinum": [("STR", 89), 9],
        },
    },

    "East/West Playmaker": {
        "Recoup": {
            "Bronze": [("STM", 95), 4],
            "Silver": [("STM", 96), 4],
            "Gold": [("STM", 97), 8],
            "Platinum": [("STM", 98), 10],
        },
        "Shifty": {
            "Bronze": [("COD", 94), ("ACC", 90), 2],
            "Silver": [("COD", 95), ("ACC", 91), 2],
            "Gold": [("COD", 96), ("ACC", 93), 6],
            "Platinum": [("COD", 97), ("ACC", 96), 8],
        },
        "Side Step": {
            "Bronze": [("JUKE", 87), 2],
            "Silver": [("JUKE", 88), 2],
            "Gold": [("JUKE", 91), 6],
            "Platinum": [("JUKE", 93), 8],
        },
        "360": {
            "Bronze": [("SPM", 83), 3],
            "Silver": [("SPM", 85), 3],
            "Gold": [("SPM", 87), 7],
            "Platinum": [("SPM", 89), 9],
        },
        "Arm Bar": {
            "Bronze": [("SFA", 83), 3],
            "Silver": [("SFA", 86), 3],
            "Gold": [("SFA", 90), 7],
            "Platinum": [("SFA", 96), 9],
        },
    },

    "Elusive Bruiser": {
        "Shifty": {
            "Bronze": [("COD", 94), ("ACC", 90), 4],
            "Silver": [("COD", 95), ("ACC", 91), 4],
            "Gold": [("COD", 96), ("ACC", 93), 8],
            "Platinum": [("COD", 97), ("ACC", 96), 10],
        },
        "Headfirst": {
            "Bronze": [("TRK", 85), 3],
            "Silver": [("TRK", 88), 3],
            "Gold": [("TRK", 92), 7],
            "Platinum": [("TRK", 95), 9],
        },
        "Side Step": {
            "Bronze": [("JUKE", 87), 3],
            "Silver": [("JUKE", 88), 3],
            "Gold": [("JUKE", 91), 7],
            "Platinum": [("JUKE", 93), 9],
        },
        "Downhill": {
            "Bronze": [("BTK", 84), 3],
            "Silver": [("BTK", 87), 3],
            "Gold": [("BTK", 92), 7],
            "Platinum": [("BTK", 94), 9],
        },
        "Arm Bar": {
            "Bronze": [("SFA", 83), 3],
            "Silver": [("SFA", 86), 3],
            "Gold": [("SFA", 90), 7],
            "Platinum": [("SFA", 96), 9],
        },
    },

    "North/South Receiver": {
        "Balanced": {
            "Bronze": [("STR", 83), 3],
            "Silver": [("STR", 85), 3],
            "Gold": [("STR", 87), 7],
            "Platinum": [("STR", 89), 9],
        },
        "Arm Bar": {
            "Bronze": [("SFA", 81), 4],
            "Silver": [("SFA", 85), 4],
            "Gold": [("SFA", 90), 8],
            "Platinum": [("SFA", 93), 10],
        },
        "Safety Valve": {
            "Bronze": [("CTH", 73), 2],
            "Silver": [("CTH", 76), 2],
            "Gold": [("CTH", 80), 6],
            "Platinum": [("CTH", 85), 8],
        },
        "Headfirst": {
            "Bronze": [("TRK", 83), 2],
            "Silver": [("TRK", 86), 2],
            "Gold": [("TRK", 89), 6],
            "Platinum": [("TRK", 91), 8],
        },
        "Downhill": {
            "Bronze": [("BTK", 84), 2],
            "Silver": [("BTK", 87), 2],
            "Gold": [("BTK", 92), 6],
            "Platinum": [("BTK", 94), 8],
        },
    },

    "North/South Blocker": {
        "Headfirst": {
            "Bronze": [("TRK", 85), 3],
            "Silver": [("TRK", 88), 3],
            "Gold": [("TRK", 92), 7],
            "Platinum": [("TRK", 95), 9],
        },
        "Balanced": {
            "Bronze": [("SFA", 81), 4],
            "Silver": [("SFA", 86), 4],
            "Gold": [("SFA", 91), 8],
            "Platinum": [("SFA", 96), 10],
        },
        "Ball Security": {
            "Bronze": [("CAR", 90), 2],
            "Silver": [("CAR", 91), 2],
            "Gold": [("CAR", 92), 6],
            "Platinum": [("CAR", 94), 8],
        },
        "Strong Grip": {
            "Bronze": [("STR", 83), 3],
            "Silver": [("STR", 85), 3],
            "Gold": [("STR", 87), 7],
            "Platinum": [("STR", 92), 9],
        },
        "Sidekick": {
            "Bronze": [("PBK", 63), 2],
            "Silver": [("PBK", 65), 2],
            "Gold": [("PBK", 67), 6],
            "Platinum": [("PBK", 70), 8],
        },
    },

# ───────────── FB ─────────────

    "Blocking": {
        "Strong Grip": {
            "Bronze": [("STR", 86), 2],
            "Silver": [("STR", 90), 2],
            "Gold": [("STR", 94), 6],
            "Platinum": [("STR", 98), 8],
        },
        "Second Level": {
            "Bronze": [("IBL", 84), 2],
            "Silver": [("IBL", 89), 2],
            "Gold": [("IBL", 93), 6],
            "Platinum": [("IBL", 97), 8],
        },
        "Pocket Shield": {
            "Bronze": [("PBK", 69), 3],
            "Silver": [("PBK", 71), 3],
            "Gold": [("PBK", 73), 7],
            "Platinum": [("PBK", 75), 9],
        },
        "Sidekick": {
            "Bronze": [("PBK", 75), 3],
            "Silver": [("PBK", 80), 3],
            "Gold": [("PBK", 86), 7],
            "Platinum": [("PBK", 93), 9],
        },
        "Screen Enforcer": {
            "Bronze": [("IBL", 75), 4],
            "Silver": [("IBL", 80), 4],
            "Gold": [("IBL", 86), 8],
            "Platinum": [("IBL", 93), 10],
        },
    },
    
    
    "Utility": {
        "Sidekick": {
            "Bronze": [("PBK", 75), 2],
            "Silver": [("PBK", 80), 2],
            "Gold": [("PBK", 86), 6],
            "Platinum": [("PBK", 93), 8],
        },
        "Screen Enforcer": {
            "Bronze": [("IBL", 73), 2],
            "Silver": [("IBL", 76), 2],
            "Gold": [("IBL", 80), 4],
            "Platinum": [("IBL", 85), 8],
        },
        "Balanced": {
            "Bronze": [("STR", 85), 3],
            "Silver": [("STR", 87), 3],
            "Gold": [("STR", 94), 7],
            "Platinum": [("STR", 98), 9],
        },
        "Recoup": {
            "Bronze": [("STM", 88), 4],
            "Silver": [("STM", 91), 4],
            "Gold": [("STM", 95), 8],
            "Platinum": [("STM", 99), 10],
        },
        "Safety Valve": {
            "Bronze": [("CTH", 75), 3],
            "Silver": [("CTH", 80), 3],
            "Gold": [("CTH", 86), 7],
            "Platinum": [("CTH", 94), 9],
        },
    },

# ───────────── WR ─────────────

    "Speedster": {
        "Takeoff": {
            "Bronze": [("ACC", 95), 2],
            "Silver": [("ACC", 96), 2],
            "Gold": [("ACC", 97), 6],
            "Platinum": [("ACC", 98), 8],
        },
        "Shifty": {
            "Bronze": [("COD", 94), ("ACC", 90), 3],
            "Silver": [("COD", 95), ("ACC", 91), 3],
            "Gold": [("COD", 96), ("ACC", 93), 7],
            "Platinum": [("COD", 97), ("ACC", 96), 9],
        },
        "Double Dip": {
            "Bronze": [("DRR", 83), 3],
            "Silver": [("DRR", 86), 3],
            "Gold": [("DRR", 88), 7],
            "Platinum": [("DRR", 90), 9],
        },
        "Recoup": {
            "Bronze": [("STM", 95), 4],
            "Silver": [("STM", 96), 4],
            "Gold": [("STM", 97), 8],
            "Platinum": [("STM", 98), 10],
        },
        "Side Step": {
            "Bronze": [("JUKE", 86), 3],
            "Silver": [("JUKE", 87), 3],
            "Gold": [("JUKE", 91), 7],
            "Platinum": [("JUKE", 93), 9],
        },
    },

    "Contested Specialist": {
        "50/50": {
            "Bronze": [("SPC", 89), 2],
            "Silver": [("SPC", 91), 2],
            "Gold": [("SPC", 94), 4],
            "Platinum": [("SPC", 96), 8],
        },
        "Workhorse": {
            "Bronze": [("TGH", 90), 3],
            "Silver": [("TGH", 92), 3],
            "Gold": [("TGH", 94), 7],
            "Platinum": [("TGH", 96), 9],
        },
        "Balanced": {
            "Bronze": [("BTK", 80), 4],
            "Silver": [("BTK", 82), 4],
            "Gold": [("BTK", 86), 8],
            "Platinum": [("BTK", 90), 10],
        },
        "Headfirst": {
            "Bronze": [("TRK", 85), 3],
            "Silver": [("TRK", 88), 3],
            "Gold": [("TRK", 92), 7],
            "Platinum": [("TRK", 95), 9],
        },
        "Downhill": {
            "Bronze": [("BTK", 84), 2],
            "Silver": [("BTK", 87), 2],
            "Gold": [("BTK", 92), 6],
            "Platinum": [("BTK", 94), 8],
        },
    },

    "Elusive Route Runner": {
        "360": {
            "Bronze": [("SPM", 83), 3],
            "Silver": [("SPM", 85), 3],
            "Gold": [("SPM", 87), 7],
            "Platinum": [("SPM", 89), 9],
        },
        "Cutter": {
            "Bronze": [("MRR", 86), 2],
            "Silver": [("MRR", 88), 2],
            "Gold": [("MRR", 91), 6],
            "Platinum": [("MRR", 93), 8],
        },
        "Double Dip": {
            "Bronze": [("DRR", 83), 4],
            "Silver": [("DRR", 86), 4],
            "Gold": [("DRR", 88), 8],
            "Platinum": [("DRR", 90), 10],
        },
        "Recoup": {
            "Bronze": [("STM", 95), 3],
            "Silver": [("STM", 96), 3],
            "Gold": [("STM", 97), 7],
            "Platinum": [("STM", 98), 9],
        },
        "Side Step": {
            "Bronze": [("JUKE", 86), 3],
            "Silver": [("JUKE", 87), 3],
            "Gold": [("JUKE", 91), 7],
            "Platinum": [("JUKE", 93), 9],
        },
    },

    "Gadget": {
        "Side Step": {
            "Bronze": [("JUKE", 85), 3],
            "Silver": [("JUKE", 87), 3],
            "Gold": [("JUKE", 90), 7],
            "Platinum": [("JUKE", 93), 9],
        },
        "Sleight Of Hand": {
            "Bronze": [("PAC", 84), 2],
            "Silver": [("PAC", 86), 2],
            "Gold": [("PAC", 90), 6],
            "Platinum": [("PAC", 95), 8],
        },
        "Dot!": {
            "Bronze": [("DAC", 85), 3],
            "Silver": [("DAC", 87), 3],
            "Gold": [("DAC", 90), 7],
            "Platinum": [("DAC", 93), 9],
        },
        "Magician": {
            "Bronze": [("SPD", 84), 3],
            "Silver": [("SPD", 86), 3],
            "Gold": [("SPD", 91), 7],
            "Platinum": [("SPD", 92), 9],
        },
        "Option King": {
            "Bronze": [("BTK", 81), 3],
            "Silver": [("BTK", 86), 3],
            "Gold": [("BTK", 91), 7],
            "Platinum": [("BTK", 97), 9],
        },
    },
    
    "Gritty Possession WR": {
        "Second Level": {
            "Bronze": [("IBL", 83), 4],
            "Silver": [("IBL", 85), 4],
            "Gold": [("IBL", 87), 8],
            "Platinum": [("IBL", 91), 10],
        },
        "Outside Shield": {
            "Bronze": [("RBF", 69), 4],
            "Silver": [("RBF", 71), 4],
            "Gold": [("RBF", 72), 8],
            "Platinum": [("RBF", 78), 10],
        },
        "Strong Grip": {
            "Bronze": [("STR", 85), 3],
            "Silver": [("STR", 89), 3],
            "Gold": [("STR", 93), 7],
            "Platinum": [("STR", 97), 9],
        },
        "Workhorse": {
            "Bronze": [("TGH", 90), 2],
            "Silver": [("TGH", 92), 2],
            "Gold": [("TGH", 94), 6],
            "Platinum": [("TGH", 96), 8],
        },
        "Sure Hands": {
            "Bronze": [("CIT", 86), 3],
            "Silver": [("CIT", 88), 3],
            "Gold": [("CIT", 91), 7],
            "Platinum": [("CIT", 94), 9],
        },
    },

    "Physical Route Runner WR": {
        "Sure Hands": {
            "Bronze": [("CIT", 86), 2],
            "Silver": [("CIT", 88), 2],
            "Gold": [("CIT", 91), 6],
            "Platinum": [("CIT", 94), 8],
        },
        "Downhill": {
            "Bronze": [("BTK", 84), 2],
            "Silver": [("BTK", 87), 2],
            "Gold": [("BTK", 92), 6],
            "Platinum": [("BTK", 94), 8],
        },
        "50/50": {
            "Bronze": [("SPC", 89), 2],
            "Silver": [("SPC", 91), 2],
            "Gold": [("SPC", 94), 4],
            "Platinum": [("SPC", 96), 8],
        },
        "Press Pro": {
            "Bronze": [("RLS", 84), 4],
            "Silver": [("RLS", 86), 4],
            "Gold": [("RLS", 88), 8],
            "Platinum": [("RLS", 90), 10],
        },
        "Cutter": {
            "Bronze": [("MRR", 86), 3],
            "Silver": [("MRR", 88), 3],
            "Gold": [("MRR", 91), 7],
            "Platinum": [("MRR", 93), 9],
        },
    },

    "Route Artist": {
        "Sure Hands": {
            "Bronze": [("CIT", 86), 3],
            "Silver": [("CIT", 88), 3],
            "Gold": [("CIT", 91), 7],
            "Platinum": [("CIT", 94), 9],
        },
        "Lay Out": {
            "Bronze": [("SPC", 88), 3],
            "Silver": [("SPC", 89), 3],
            "Gold": [("SPC", 92), 7],
            "Platinum": [("SPC", 94), 9],
        },
        "Recoup": {
            "Bronze": [("STM", 95), 4],
            "Silver": [("STM", 96), 4],
            "Gold": [("STM", 97), 8],
            "Platinum": [("STM", 98), 10],
        },
        "Double Dip": {
            "Bronze": [("DRR", 83), 2],
            "Silver": [("DRR", 86), 2],
            "Gold": [("DRR", 88), 6],
            "Platinum": [("DRR", 90), 8],
        },
        "Cutter": {
            "Bronze": [("MRR", 86), 2],
            "Silver": [("MRR", 88), 2],
            "Gold": [("MRR", 91), 6],
            "Platinum": [("MRR", 93), 8],
        },
    },



# ───────────── TE ─────────────

    "Vertical Threat": {
        "Workhorse": {
            "Bronze": [("TGH", 90), 3],
            "Silver": [("TGH", 92), 3],
            "Gold": [("TGH", 94), 7],
            "Platinum": [("TGH", 96), 9],
        },
        "Balanced": {
            "Bronze": [("BTK", 82), 3],
            "Silver": [("STR", 84), 3],
            "Gold": [("STR", 87), 7],
            "Platinum": [("STR", 90), 9],
        },
        "Takeoff": {
            "Bronze": [("ACC", 95), 2],
            "Silver": [("ACC", 96), 2],
            "Gold": [("ACC", 97), 6],
            "Platinum": [("ACC", 98), 8],
        },
        "Recoup": {
            "Bronze": [("STA", 95), 2],
            "Silver": [("STA", 96), 2],
            "Gold": [("STA", 97), 6],
            "Platinum": [("STA", 98), 8],
        },
        "50/50": {
            "Bronze": [("SPC", 86), 4],
            "Silver": [("SPC", 88), 4],
            "Gold": [("SPC", 92), 8],
            "Platinum": [("SPC", 94), 10],
        },
    },


    "Gritty Possession TE": {
        "Workhorse": {
            "Bronze": [("TOU", 90), 2],
            "Silver": [("TOU", 92), 2],
            "Gold": [("TOU", 94), 6],
            "Platinum": [("TOU", 96), 8],
        },
        "Strong Grip": {
            "Bronze": [("STR", 85), 3],
            "Silver": [("STR", 89), 3],
            "Gold": [("STR", 93), 7],
            "Platinum": [("STR", 97), 9],
        },
        "Sure Hands": {
            "Bronze": [("CIT", 86), 3],
            "Silver": [("CIT", 88), 3],
            "Gold": [("CIT", 91), 7],
            "Platinum": [("CIT", 94), 9],
        },
        "Outside Shield": {
            "Bronze": [("RBF", 69), 4],
            "Silver": [("RBF", 71), 4],
            "Gold": [("RBF", 72), 8],
            "Platinum": [("RBF", 78), 10],
        },
        "Battering Ram": {
            "Bronze": [("TOU", 90), 4],
            "Silver": [("TOU", 91), 4],
            "Gold": [("TOU", 92), 8],
            "Platinum": [("TOU", 94), 10],
        },
    },

    "Physical Route Runner TE": {
        "Balanced": {
            "Bronze": [("SPC", 89), 2],
            "Silver": [("SPC", 91), 2],
            "Gold": [("SPC", 94), 4],
            "Platinum": [("SPC", 96), 8],
        },
        "50/50": {
            "Bronze": [("SPC", 89), 2],
            "Silver": [("SPC", 91), 2],
            "Gold": [("SPC", 94), 4],
            "Platinum": [("SPC", 96), 8],
        },
        "Cutter": {
            "Bronze": [("MRR", 86), 3],
            "Silver": [("MRR", 88), 3],
            "Gold": [("MRR", 91), 7],
            "Platinum": [("MRR", 93), 9],
        },
        "Downhill": {
            "Bronze": [("BTK", 84), 2],
            "Silver": [("BTK", 87), 2],
            "Gold": [("BTK", 92), 6],
            "Platinum": [("BTK", 94), 8],
        },
        "Sure Hands": {
            "Bronze": [("CIT", 86), 2],
            "Silver": [("CIT", 88), 2],
            "Gold": [("CIT", 91), 6],
            "Platinum": [("CIT", 94), 8],
        },
    },

    "Possession": {
        "Sure Hands": {
            "Bronze": [("CIT", 83), 2],
            "Silver": [("CIT", 84), 2],
            "Gold": [("CIT", 88), 6],
            "Platinum": [("CIT", 90), 8],
        },
        "Wear Down": {
            "Bronze": [("PBK", 84), 4],
            "Silver": [("PBK", 88), 4],
            "Gold": [("PBK", 93), 8],
            "Platinum": [("PBK", 97), 10],
        },
        "Strong Grip": {
            "Bronze": [("STR", 87), 3],
            "Silver": [("STR", 91), 3],
            "Gold": [("STR", 95), 7],
            "Platinum": [("STR", 99), 9],
        },
        "Outside Shield": {
            "Bronze": [("RBF", 69), 3],
            "Silver": [("RBF", 71), 3],
            "Gold": [("RBF", 72), 7],
            "Platinum": [("RBF", 78), 9],
        },
        "Balanced": {
            "Bronze": [("BTK", 82), 2],
            "Silver": [("STR", 84), 2],
            "Gold": [("STR", 87), 6],
            "Platinum": [("STR", 90), 8],
        },
    },


    "Pure Blocker": {
        "Strong Grip": {
            "Bronze": [("STR", 94), 2],
            "Silver": [("STR", 95), 2],
            "Gold": [("STR", 96), 6],
            "Platinum": [("STR", 97), 8],
        },
        "Quick Drop": {
            "Bronze": [("ACC", 83), 2],
            "Silver": [("ACC", 85), 2],
            "Gold": [("ACC", 87), 6],
            "Platinum": [("ACC", 89), 8],
        },
        "Outside Shield": {
            "Bronze": [("RBF", 69), 4],
            "Silver": [("RBF", 71), 4],
            "Gold": [("RBF", 72), 8],
            "Platinum": [("RBF", 78), 10],
        },
        "Pocket Shield": {
            "Bronze": [("PBP", 69), 3],
            "Silver": [("PBP", 71), 3],
            "Gold": [("PBP", 73), 7],
            "Platinum": [("PBP", 75), 9],
        },
        "Second Level": {
            "Bronze": [("IBL", 89), 3],
            "Silver": [("IBL", 91), 3],
            "Gold": [("IBL", 93), 7],
            "Platinum": [("IBL", 94), 9],
        },
    },


# ───────────── OL ─────────────

    "Agile": {
        "Screen Enforcer": {
            "Bronze": [("IBL", 88), 2],
            "Silver": [("IBL", 89), 2],
            "Gold": [("IBL", 91), 4],
            "Platinum": [("IBL", 94), 8],
        },
        "Quick Step": {
            "Bronze": [("ACC", 79), 2],
            "Silver": [("ACC", 81), 2],
            "Gold": [("ACC", 83), 6],
            "Platinum": [("ACC", 84), 8],
        },
        "Option Shield": {
            "Bronze": [("RBF", 88), 3],
            "Silver": [("RBF", 89), 3],
            "Gold": [("RBF", 91), 7],
            "Platinum": [("RBF", 93), 9],
        },
        "Outside Shield": {
            "Bronze": [("RBF", 88), 3],
            "Silver": [("RBF", 89), 3],
            "Gold": [("RBF", 92), 7],
            "Platinum": [("RBF", 93), 9],
        },
        "Quick Drop": {
            "Bronze": [("ACC", 82), ("SPD", 68), 4],
            "Silver": [("ACC", 82), ("SPD", 69), 4],
            "Gold": [("ACC", 83), ("SPD", 69), 8],
            "Platinum": [("ACC", 84), ("SPD", 70), 10],
        },
    },

    "Pass Protector": {
        "Pocket Shield": {
            "Bronze": [("PBP", 84), 3],
            "Silver": [("PBP", 86), 3],
            "Gold": [("PBP", 91), 7],
            "Platinum": [("PBP", 95), 9],
        },
        "Quick Drop": {
            "Bronze": [("ACC", 82), ("SPD", 68), 2],
            "Silver": [("ACC", 82), ("SPD", 69), 2],
            "Gold": [("ACC", 83), ("SPD", 69), 6],
            "Platinum": [("ACC", 84), ("SPD", 70), 8],
        },
        "PA Shield": {
            "Bronze": [("PBP", 84), 4],
            "Silver": [("PBP", 86), 4],
            "Gold": [("PBP", 91), 8],
            "Platinum": [("PBP", 95), 10],
        },
        "Strong Grip": {
            "Bronze": [("STR", 94), 2],
            "Silver": [("STR", 95), 2],
            "Gold": [("STR", 96), 6],
            "Platinum": [("STR", 97), 8],
        },
        "Wear Down": {
            "Bronze": [("PBK", 85), 3],
            "Silver": [("PBK", 88), 3],
            "Gold": [("PBK", 93), 7],
            "Platinum": [("PBK", 95), 9],
        },
    },

    "Raw Strength": {
        "Strong Grip": {
            "Bronze": [("STR", 94), 2],
            "Silver": [("STR", 95), 2],
            "Gold": [("STR", 96), 6],
            "Platinum": [("STR", 97), 8],
        },
        "Second Level": {
            "Bronze": [("IBL", 89), 2],
            "Silver": [("IBL", 91), 2],
            "Gold": [("IBL", 93), 6],
            "Platinum": [("IBL", 94), 8],
        },
        "Inside Shield": {
            "Bronze": [("RBP", 86), 3],
            "Silver": [("RBP", 88), 3],
            "Gold": [("RBP", 91), 7],
            "Platinum": [("RBP", 93), 9],
        },
        "Ground N Pound": {
            "Bronze": [("RBK", 83), 4], # ESTIMATED
            "Silver": [("RBK", 85), 4], # ESTIMATED
            "Gold": [("RBK", 88), 8], # ESTIMATED
            "Platinum": [("RBK", 91), 10], # ESTIMATED
        },
        "Workhorse": {
            "Bronze": [("TGH", 90), 2], # ESTIMATED
            "Silver": [("TGH", 92), 2], # ESTIMATED
            "Gold": [("TGH", 94), 6], # ESTIMATED
            "Platinum": [("TGH", 96), 8], # ESTIMATED
        },
    },

    "Well Rounded": {
        "Pocket Shield": {
            "Bronze": [("PBP", 84), 3],
            "Silver": [("PBP", 86), 3],
            "Gold": [("PBP", 91), 7],
            "Platinum": [("PBP", 95), 9],
        },
        "Outside Shield": {
            "Bronze": [("RBF", 88), 3],
            "Silver": [("RBF", 89), 3],
            "Gold": [("RBF", 92), 7],
            "Platinum": [("RBF", 93), 9],
        },
        "Strong Grip": {
            "Bronze": [("STR", 94), 2],
            "Silver": [("STR", 95), 2],
            "Gold": [("STR", 96), 6],
            "Platinum": [("STR", 97), 8],
        },
        "Option Shield": {
            "Bronze": [("RBF", 88), 2],
            "Silver": [("RBF", 89), 2],
            "Gold": [("RBF", 91), 6],
            "Platinum": [("RBF", 93), 8],
        },
        "Inside Shield": {
            "Bronze": [("RBP", 86), 3],
            "Silver": [("RBP", 88), 3],
            "Gold": [("RBP", 91), 7],
            "Platinum": [("RBP", 93), 9],
        },
    },


# ───────────── DL ─────────────

    "Edge Setter": {
        "Grip Breaker": {
            "Bronze": [("STR", 94), 2],
            "Silver": [("STR", 95), 2],
            "Gold": [("STR", 96), 6],
            "Platinum": [("STR", 97), 8],
        },
        "Inside Disruptor": {
            "Bronze": [("BSH", 87), 3],
            "Silver": [("BSH", 89), 3],
            "Gold": [("BSH", 92), 7],
            "Platinum": [("BSH", 94), 9],
        },
        "Outside Disruptor": {
            "Bronze": [("BSH", 88), 3],
            "Silver": [("BSH", 90), 3],
            "Gold": [("BSH", 93), 7],
            "Platinum": [("BSH", 95), 9],
        },
        "Option Disruptor": {
            "Bronze": [("PRC", 85), 3],
            "Silver": [("PRC", 88), 3],
            "Gold": [("PRC", 90), 7],
            "Platinum": [("PRC", 94), 9],
        },
        "Workhorse": {
            "Bronze": [("TGH", 90), 4],
            "Silver": [("TGH", 92), 4],
            "Gold": [("TGH", 94), 8],
            "Platinum": [("TGH", 96), 10],
        },
    },

    "Physical Freak": {
        "Grip Breaker": {
            "Bronze": [("STR", 94), 2],
            "Silver": [("STR", 95), 2],
            "Gold": [("STR", 96), 6],
            "Platinum": [("STR", 97), 8],
        },
        "Pocket Disruptor": {
            "Bronze": [("FMV", 88), ("PMV", 88), 3],
            "Silver": [("FMV", 89), ("PMV", 89), 3],
            "Gold": [("FMV", 91), ("PMV", 91), 7],
            "Platinum": [("FMV", 94), ("PMV", 94), 9],
        },
        "Inside Disruptor": {
            "Bronze": [("BSH", 87), 3],
            "Silver": [("BSH", 89), 3],
            "Gold": [("BSH", 92), 7],
            "Platinum": [("BSH", 94), 9],
        },
        "Workhorse": {
            "Bronze": [("TGH", 90), 3],
            "Silver": [("TGH", 92), 3],
            "Gold": [("TGH", 94), 7],
            "Platinum": [("TGH", 96), 9],
        },
        "Quick Jump": {
            "Bronze": [("ACC", 89), 2],
            "Silver": [("ACC", 90), 2],
            "Gold": [("ACC", 91), 6],
            "Platinum": [("ACC", 93), 8],
        },
    },


    "Power Rusher": {
        "Pocket Disruptor": {
            "Bronze": [("FMV", 88), ("PMV", 88), 3],
            "Silver": [("FMV", 89), ("PMV", 89), 3],
            "Gold": [("FMV", 91), ("PMV", 91), 7],
            "Platinum": [("FMV", 94), ("PMV", 94), 9],
        },
        "Duress": {
            "Bronze": [("PMV", 88), ("FMV", 88), 2],
            "Silver": [("PMV", 89), ("FMV", 89), 2],
            "Gold": [("PMV", 91), ("FMV", 91), 6],
            "Platinum": [("PMV", 94), ("FMV", 94), 8],
        },
        "Grip Breaker": {
            "Bronze": [("STR", 94), 2],
            "Silver": [("STR", 95), 2],
            "Gold": [("STR", 96), 6],
            "Platinum": [("STR", 97), 8],
        },
        "Workhorse": {
            "Bronze": [("TGH", 90), 4],
            "Silver": [("TGH", 92), 4],
            "Gold": [("TGH", 94), 8],
            "Platinum": [("TGH", 96), 10],
        },
        "Take Down": {
            "Bronze": [("TAK", 86), 3],
            "Silver": [("TAK", 88), 3],
            "Gold": [("TAK", 90), 7],
            "Platinum": [("TAK", 92), 9],
        },
    },


    "Speed Rusher": {
        "Quick Jump": {
            "Bronze": [("ACC", 89), 2],
            "Silver": [("ACC", 90), 2],
            "Gold": [("ACC", 91), 6],
            "Platinum": [("ACC", 93), 8],
        },
        "Duress": {
            "Bronze": [("PMV", 88), ("FMV", 88), 3],
            "Silver": [("PMV", 89), ("FMV", 89), 3],
            "Gold": [("PMV", 91), ("FMV", 91), 7],
            "Platinum": [("PMV", 94), ("FMV", 94), 9],
        },
        "Take Down": {
            "Bronze": [("TAK", 82), 3],
            "Silver": [("TAK", 87), 3],
            "Gold": [("TAK", 91), 7],
            "Platinum": [("TAK", 97), 9],
        },
        "Pocket Disruptor": {
            "Bronze": [("FMV", 88), ("PMV", 88), 2],
            "Silver": [("FMV", 89), ("PMV", 89), 2],
            "Gold": [("FMV", 91), ("PMV", 91), 6],
            "Platinum": [("FMV", 94), ("PMV", 94), 8],
        },
        "Recoup": {
            "Bronze": [("STA", 86), 4],
            "Silver": [("STA", 88), 4],
            "Gold": [("STA", 90), 8],
            "Platinum": [("STA", 92), 10],
        },
    },



    "Gap Specialist": {
        "Grip Breaker": {
            "Bronze": [("STR", 94), 2],
            "Silver": [("STR", 95), 2],
            "Gold": [("STR", 96), 6],
            "Platinum": [("STR", 97), 8],
        },
        "Inside Disruptor": {
            "Bronze": [("BSH", 87), 3],
            "Silver": [("BSH", 89), 3],
            "Gold": [("BSH", 92), 7],
            "Platinum": [("BSH", 94), 9],
        },
        "Outside Disruptor": {
            "Bronze": [("BSH", 88), 3],
            "Silver": [("BSH", 90), 3],
            "Gold": [("BSH", 93), 7],
            "Platinum": [("BSH", 95), 9],
        },
        "Option Disruptor": {
            "Bronze": [("PRC", 85), 3],
            "Silver": [("PRC", 88), 3],
            "Gold": [("PRC", 90), 7],
            "Platinum": [("PRC", 94), 9],
        },
        "Workhorse": {
            "Bronze": [("TGH", 90), 4],
            "Silver": [("TGH", 92), 4],
            "Gold": [("TGH", 94), 8],
            "Platinum": [("TGH", 96), 10],
        },
    },


# ───────────── LB ─────────────

    "Lurker": {
        "House Call": {
            "Bronze": [("CTH", 71), 2],
            "Silver": [("CTH", 73), 2],
            "Gold": [("CTH", 75), 6],
            "Platinum": [("CTH", 78), 8],
        },
        "Knockout": {
            "Bronze": [("ZCV", 84), 3],
            "Silver": [("ZCV", 85), 3],
            "Gold": [("ZCV", 88), 7],
            "Platinum": [("ZCV", 92), 9],
        },
        "Bouncer": {
            "Bronze": [("ZCV", 83), 2],
            "Silver": [("ZCV", 87), 2],
            "Gold": [("ZCV", 89), 6],  # ESTIMATED
            "Platinum": [("ZCV", 91), 8], # ESTIMATED
        },
        "Hammer": {
            "Bronze": [("POW", 88), 3],
            "Silver": [("POW", 90), 3],
            "Gold": [("POW", 91), 7],
            "Platinum": [("POW", 93), 9],
        },
        "Wrap Up": {
            "Bronze": [("TAK", 88), 4],
            "Silver": [("TAK", 90), 4],
            "Gold": [("TAK", 92), 8],
            "Platinum": [("TAK", 93), 10],
        },
    },
    
    "Signal Caller": {
        "Grip Breaker": {
            "Bronze": [("STR", 87), 3], 
            "Silver": [("STR", 90), 3],
            "Gold": [("STR", 93), 7],
            "Platinum": [("STR", 95), 9],
        },
        "Workhorse": {
            "Bronze": [("TGH", 90), 3],
            "Silver": [("TGH", 92), 3],
            "Gold": [("TGH", 94), 7],
            "Platinum": [("TGH", 96), 9],
        },
        "Inside Disruptor": {
            "Bronze": [("BSH", 85), 2],
            "Silver": [("BSH", 87), 2],
            "Gold": [("BSH", 90), 6],
            "Platinum": [("BSH", 92), 8],
        },
        "Wrap Up": {
            "Bronze": [("TAK", 88), 2],
            "Silver": [("TAK", 90), 2],
            "Gold": [("TAK", 92), 6],
            "Platinum": [("TAK", 93), 8],
        },
        "Hammer": {
            "Bronze": [("POW", 88), 4],
            "Silver": [("POW", 90), 4],
            "Gold": [("POW", 91), 8],
            "Platinum": [("POW", 93), 10],
        },
    },

    "Thumper": {
        "Wrap Up": {
            "Bronze": [("TAK", 88), 2],
            "Silver": [("TAK", 90), 2],
            "Gold": [("TAK", 92), 6],
            "Platinum": [("TAK", 93), 8],
        },
        "Aftershock": {
            "Bronze": [("POW", 88), 4],
            "Silver": [("POW", 90), 4],
            "Gold": [("POW", 92), 8],
            "Platinum": [("POW", 94), 10],
        },
        "Blow Up": {
            "Bronze": [("POW", 80), 2],
            "Silver": [("POW", 82), 2],
            "Gold": [("POW", 85), 6],
            "Platinum": [("POW", 88), 8],
        },
        "Outside Disruptor": {
            "Bronze": [("BSH", 83), 3],
            "Silver": [("BSH", 85), 3],
            "Gold": [("BSH", 87), 7],
            "Platinum": [("BSH", 89), 9],
        },
        "Grip Breaker": {
            "Bronze": [("STR", 87), 3],
            "Silver": [("STR", 90), 3],
            "Gold": [("STR", 93), 7],
            "Platinum": [("STR", 95), 9],
        },
    },

# ───────────── CB ─────────────
    "Boundary": {
        "Jammer": {
            "Bronze": [("PRS", 82), 3],
            "Silver": [("PRS", 84), 3],
            "Gold": [("PRS", 87), 7],
            "Platinum": [("PRS", 91), 9],
        },
        "Blanket Coverage": {
            "Bronze": [("MCV", 84), 2],
            "Silver": [("MCV", 86), 2],
            "Gold": [("MCV", 88), 6],
            "Platinum": [("MCV", 92), 8],
        },
        "Lay Out": {
            "Bronze": [("SPC", 72), 2],
            "Silver": [("SPC", 74), 2],
            "Gold": [("SPC", 77), 6],
            "Platinum": [("SPC", 80), 8],
        },
        "Wrap Up": {
            "Bronze": [("TAK", 88), 3],
            "Silver": [("TAK", 90), 3],
            "Gold": [("TAK", 92), 7],
            "Platinum": [("TAK", 93), 9],
        },
        "Quick Jump": {
            "Bronze": [("ACC", 93), 4],
            "Silver": [("ACC", 94), 4],
            "Gold": [("ACC", 95), 8],
            "Platinum": [("ACC", 96), 10],
        },
    },

    "Bump and Run": {
        "Blanket Coverage": {
            "Bronze": [("MCV", 84), 2],
            "Silver": [("MCV", 86), 2],
            "Gold": [("MCV", 88), 6],
            "Platinum": [("MCV", 92), 8],
        },
        "Jammer": {
            "Bronze": [("PRS", 82), 2],
            "Silver": [("PRS", 84), 2],
            "Gold": [("PRS", 87), 6],
            "Platinum": [("PRS", 91), 8],
        },
        "House Call": {
            "Bronze": [("CTH", 75), 3],
            "Silver": [("CTH", 78), 3],
            "Gold": [("CTH", 81), 7],
            "Platinum": [("CTH", 83), 9],
        },
        "Ball Hawk": {
            "Bronze": [("AWR", 86), 3],
            "Silver": [("AWR", 88), 3],
            "Gold": [("AWR", 91), 7],
            "Platinum": [("AWR", 94), 9],
        },
        "Knockout": {
            "Bronze": [("MCV", 86), ("ZCV", 86), 4],
            "Silver": [("MCV", 88), ("ZCV", 88), 4],
            "Gold": [("MCV", 90), ("ZCV", 90), 8],
            "Platinum": [("MCV", 94), ("ZCV", 94), 10],
        },
    },

    "Field": {
        "Wrap Up": {
            "Bronze": [("TAK", 88), 3],
            "Silver": [("TAK", 90), 3],
            "Gold": [("TAK", 92), 7],
            "Platinum": [("TAK", 93), 9],
        },
        "Robber": {
            "Bronze": [("COD", 89), 3],
            "Silver": [("COD", 90), 3],
            "Gold": [("COD", 92), 7],
            "Platinum": [("COD", 93), 9],
        },
        "Knockout": {
            "Bronze": [("MCV", 86), ("ZCV", 86), 2],
            "Silver": [("MCV", 88), ("ZCV", 88), 2],
            "Gold": [("MCV", 90), ("ZCV", 90), 6],
            "Platinum": [("MCV", 94), ("ZCV", 94), 8],
        },
        "Blanket Coverage": {
            "Bronze": [("MCV", 84), 2],
            "Silver": [("MCV", 86), 2],
            "Gold": [("MCV", 88), 6],
            "Platinum": [("MCV", 92), 8],
        },
        "Ball Hawk": {
            "Bronze": [("AWR", 86), 2],
            "Silver": [("AWR", 88), 2],
            "Gold": [("AWR", 91), 6],
            "Platinum": [("AWR", 94), 8],
        },
    },

    "Zone": {
        "Knockout": {
            "Bronze": [("MCV", 86), ("ZCV", 86), 2],
            "Silver": [("MCV", 88), ("ZCV", 88), 2],
            "Gold": [("MCV", 90), ("ZCV", 90), 6],
            "Platinum": [("MCV", 94), ("ZCV", 94), 8],
        },
        "Lay Out": {
            "Bronze": [("SPC", 72), 2],
            "Silver": [("SPC", 74), 2],
            "Gold": [("SPC", 77), 6],
            "Platinum": [("SPC", 80), 8],
        },
        "House Call": {
            "Bronze": [("CTH", 75), 3],
            "Silver": [("CTH", 78), 3],
            "Gold": [("CTH", 81), 7],
            "Platinum": [("CTH", 83), 9],
        },
        "Ball Hawk": {
            "Bronze": [("AWR", 86), 3],
            "Silver": [("AWR", 88), 3],
            "Gold": [("AWR", 91), 7],
            "Platinum": [("AWR", 94), 9],
        },
        "Bouncer": {
            "Bronze": [("ZCV", 89), 4],
            "Silver": [("ZCV", 90), 4],
            "Gold": [("ZCV", 94), 8],
            "Platinum": [("ZCV", 96), 10],  # ESTIMATED
        },
    },


# ───────────── S ─────────────

    "Box Specialist": {
        "Aftershock": {
            "Bronze": [("HPW", 88), 3],
            "Silver": [("HPW", 90), 3],
            "Gold": [("HPW", 92), 7],
            "Platinum": [("HPW", 94), 9],
        },
        "Wrap Up": {
            "Bronze": [("TAK", 88), 2],
            "Silver": [("TAK", 90), 2],
            "Gold": [("TAK", 92), 6],
            "Platinum": [("TAK", 93), 8],
        },
        "Hammer": {
            "Bronze": [("HPW", 88), 2],
            "Silver": [("HPW", 90), 2],
            "Gold": [("HPW", 91), 6],
            "Platinum": [("HPW", 93), 8],
        },
        "Blow Up": {
            "Bronze": [("PUR", 84), 3],
            "Silver": [("PUR", 85), 3],
            "Gold": [("PUR", 86), 7],
            "Platinum": [("PUR", 89), 9],
        },
        "Workhorse": {
            "Bronze": [("TGH", 90), 4],
            "Silver": [("TGH", 92), 4],
            "Gold": [("TGH", 94), 8],
            "Platinum": [("TGH", 96), 10],
        },
    },

    "Coverage Specialist": {
        "Ball Hawk": {
            "Bronze": [("AWR", 86), 2],
            "Silver": [("AWR", 88), 2],
            "Gold": [("AWR", 91), 6],
            "Platinum": [("AWR", 94), 8],
        },
        "Lay Out": {
            "Bronze": [("SPC", 72), 2],
            "Silver": [("SPC", 74), 2],
            "Gold": [("SPC", 77), 6],
            "Platinum": [("SPC", 80), 8],
        },
        "House Call": {
            "Bronze": [("CTH", 75), 3],
            "Silver": [("CTH", 78), 3],
            "Gold": [("CTH", 81), 7],
            "Platinum": [("CTH", 83), 9],
        },
        "Robber": {
            "Bronze": [("COD", 89), 4],
            "Silver": [("COD", 90), 4],
            "Gold": [("COD", 92), 8],
            "Platinum": [("COD", 93), 10],
        },
        "Knockout": {
            "Bronze": [("MCV", 86), ("ZCV", 86), 3],
            "Silver": [("MCV", 88), ("ZCV", 88), 3],
            "Gold": [("MCV", 90), ("ZCV", 90), 7],
            "Platinum": [("MCV", 94), ("ZCV", 94), 9],
        },
    },

    "Hybrid": {
        "Wrap Up": {
            "Bronze": [("TAK", 88), 2],
            "Silver": [("TAK", 90), 2],
            "Gold": [("TAK", 92), 6],
            "Platinum": [("TAK", 93), 8],
        },
        "Hammer": {
            "Bronze": [("HIT", 88), 4],
            "Silver": [("HIT", 90), 4],
            "Gold": [("HIT", 91), 8],
            "Platinum": [("HIT", 93), 10],
        },
        "Knockout": {
            "Bronze": [("MCV", 86), ("ZCV", 86), 2],
            "Silver": [("MCV", 88), ("ZCV", 88), 2],
            "Gold": [("MCV", 90), ("ZCV", 90), 6],
            "Platinum": [("MCV", 94), ("ZCV", 94), 8],
        },
        "Aftershock": {
            "Bronze": [("HIT", 88), 3],
            "Silver": [("HIT", 90), 3],
            "Gold": [("HIT", 92), 7],
            "Platinum": [("HIT", 94), 9],
        },
        "Blow Up": {
            "Bronze": [("PUR", 84), 3],
            "Silver": [("PUR", 85), 3],
            "Gold": [("PUR", 86), 7],
            "Platinum": [("PUR", 89), 9],
        },
    },


# ───────────── K/P ─────────────
    "Accurate": {
        "Chip Shot": {
            "Bronze": [("KPW", 87), 3],
            "Silver": [("KPW", 90), 3],
            "Gold": [("KPW", 92), 7],
            "Platinum": [("KPW", 94), 9],
        },
        "Deep Range": {
            "Bronze": [("KAC", 88), 3],
            "Silver": [("KAC", 88), 3],
            "Gold": [("KAC", 91), 7],
            "Platinum": [("KAC", 95), 9],
        },
        "Mega Leg": {
            "Bronze": [("KPW", 93), 3],
            "Silver": [("KPW", 93), 3],
            "Gold": [("KPW", 96), 7],
            "Platinum": [("KPW", 97), 9],
        },
    },

    "Power": {
        "Coffin Corner": {
            "Bronze": [("KPW", 85), 3],
            "Silver": [("KAC", 89), 3],
            "Gold": [("KAC", 91), 7],
            "Platinum": [("KAC", 93), 9],
        },
        "Deep Range": {
            "Bronze": [("KAC", 88), 3],
            "Silver": [("KAC", 88), 3],
            "Gold": [("KAC", 91), 7],
            "Platinum": [("KAC", 95), 9],
        },
        "Mega Leg": {
            "Bronze": [("KPW", 93), 3],
            "Silver": [("KPW", 93), 3],
            "Gold": [("KPW", 96), 7],
            "Platinum": [("KPW", 97), 9],
        },
    },
}

ability_descriptions = {
    "Extender": {
        "Bronze": "Slightly improved ability to break sacks vs defensive backs.",
        "Silver": "Moderately improved ability to break sacks vs defensive backs. Slightly improved vs. all defenders.",
        "Gold": "Significantly improved ability to break sacks vs all defenders.",
        "Platinum": "Ultimate break sack ability.",
    },
    # Add more abilities as needed
}



# Abilities (add all unique ones)
all_abilities = list(ability_stats.keys())

for ability in all_abilities:
    cursor.execute("INSERT OR IGNORE INTO abilities (name) VALUES (?)", (ability,))

for ability, tiers in ability_descriptions.items():
    for tier, description in tiers.items():
        cursor.execute("""
            INSERT INTO ability_descriptions (ability_id, tier, description)
            SELECT id, ?, ? FROM abilities WHERE name = ?
        """, (tier, description, ability))

# Archetype → Abilities
archetype_abilities = {
    
    #QB
    "Backfield Creator": ["Off Platform", "Pull Down", "On Time", "Sleight Of Hand", "Mobile Deadeye"],
    "Dual Threat": ["Downhill", "Extender", "Option King", "Dot!", "Mobile Resistance"],
    "Pocket Passer": ["Resistance", "Step Up", "Pull Down", "Dot!", "On Time"],
    "Pure Runner": ["Magician", "Shifty", "Option King", "Side Step", "Workhorse"],
    
    #HB
    "Backfield Threat": ["360", "Safety Valve", "Takeoff", "Side Step", "Recoup"],
    "Contact Seeker": ["Downhill", "Workhorse", "Battering Ram", "Ball Security", "Balanced"],
    "East/West Playmaker": ["Recoup", "Shifty", "Side Step", "360", "Arm Bar"],
    "Elusive Bruiser": ["Shifty", "Headfirst", "Side Step", "Downhill", "Arm Bar"],
    "North/South Receiver": ["Balanced", "Arm Bar", "Safety Valve", "Headfirst", "Downhill"],
    "North/South Blocker": ["Headfirst", "Balanced", "Sidekick", "Ball Security", "Strong Grip"],
    
    #FB
    "Blocking": ["Strong Grip", "Second Level", "Pocket Shield", "Sidekick", "Screen Enforcer"],
    "Utility": ["Screen Enforcer", "Balanced", "Safety Valve", "Sidekick", "Recoup"],
    
    #WR
    "Contested Specialist": ["50/50", "Workhorse", "Balanced", "Headfirst", "Downhill"],
    "Elusive Route Runner": ["360", "Cutter", "Double Dip", "Recoup", "Side Step"],
    "Gadget": ["Side Step", "Sleight Of Hand", "Dot!", "Magician", "Option King"],
    "Gritty Possession WR": ["Second Level", "Outside Shield", "Strong Grip", "Workhorse", "Sure Hands"],
    "Physical Route Runner WR": ["Downhill", "Press Pro", "Sure Hands", "50/50", "Cutter"],
    "Route Artist": ["Cutter", "Lay Out", "Recoup", "Double Dip", "Sure Hands"],
    "Speedster": ["Side Step", "Double Dip", "Takeoff", "Recoup", "Shifty"],
    
    #TE
    "Gritty Possession TE": ["Workhorse", "Strong Grip", "Sure Hands", "Outside Shield", "Battering Ram"],
    "Physical Route Runner TE": ["Balanced", "50/50", "Cutter", "Downhill", "Sure Hands"],
    "Possession": ["Sure Hands", "Wear Down", "Strong Grip", "Outside Shield", "Balanced"],
    "Pure Blocker": ["Strong Grip", "Quick Drop", "Outside Shield", "Pocket Shield", "Second Level"],
    "Vertical Threat": ["Workhorse", "Balanced", "Takeoff", "Recoup", "50/50"],

    #OL    
    "Agile": ["Screen Enforcer", "Quick Step", "Option Shield", "Outside Shield", "Quick Drop"],
    "Pass Protector": ["Pocket Shield", "Quick Drop", "PA Shield", "Strong Grip", "Wear Down"],
    "Raw Strength": ["Strong Grip", "Workhorse", "Second Level", "Inside Shield", "Ground N Pound"],
    "Well Rounded": ["Pocket Shield", "Outside Shield", "Strong Grip", "Option Shield", "Inside Shield"],
    
    #DL
    "Edge Setter": ["Grip Breaker", "Inside Disruptor", "Outside Disruptor", "Option Disruptor", "Workhorse"],
    "Gap Specialist": ["Grip Breaker", "Inside Disruptor", "Outside Disruptor", "Option Disruptor", "Workhorse"],
    "Physical Freak": ["Grip Breaker", "Pocket Disruptor", "Inside Disruptor", "Workhorse", "Quick Jump"],
    "Power Rusher": ["Pocket Disruptor", "Duress", "Grip Breaker", "Workhorse", "Take Down"],
    "Speed Rusher": ["Quick Jump", "Duress", "Take Down", "Pocket Disruptor", "Recoup"],
    
    #LB
    "Lurker": ["House Call", "Knockout", "Bouncer", "Hammer", "Wrap Up"],
    "Signal Caller": ["Grip Breaker", "Workhorse", "Inside Disruptor", "Wrap Up", "Hammer"],
    "Thumper": ["Wrap Up", "Aftershock", "Blow Up", "Outside Disruptor", "Grip Breaker"],
    
    #CB
    "Boundary": ["Jammer", "Blanket Coverage", "Lay Out", "Wrap Up", "Quick Jump"],
    "Bump and Run": ["Blanket Coverage", "Jammer", "House Call", "Ball Hawk", "Knockout"],
    "Field": ["Wrap Up", "Robber", "Knockout", "Blanket Coverage", "Ball Hawk"],
    "Zone": ["Knockout", "Lay Out", "House Call", "Ball Hawk", "Bouncer"],
    
    #S
    "Box Specialist": ["Aftershock", "Wrap Up", "Hammer", "Blow Up", "Workhorse"],
    "Coverage Specialist": ["Ball Hawk", "Lay Out", "House Call", "Robber", "Knockout"],
    "Hybrid": ["Wrap Up", "Hammer", "Knockout", "Aftershock", "Blow Up"],
    
    #K/P
    "Accurate": ["Chip Shot", "Deep Range", "Mega Leg"],
    "Power": ["Deep Range", "Mega Leg", "Coffin Corner"]
}

for archetype, abilities in archetype_abilities.items():
    for order, ability in enumerate(abilities, 1):
        cursor.execute("""
            INSERT INTO archetype_abilities (archetype_id, ability_id, ability_order)
            SELECT a.id, b.id, ?
            FROM archetypes a, abilities b
            WHERE a.name = ? AND b.name = ?
        """, (order, archetype, ability))

# INSERT PER-ARCHETYPE TIERS
for archetype, abilities in archetype_abilities.items():
    for ability in abilities:
        # fallback to global ability_stats if per-archetype version doesn't exist
        if archetype in archetype_ability_tiers and ability in archetype_ability_tiers[archetype]:
            tier_data = archetype_ability_tiers[archetype][ability]
            insert_archetype_specific_tiers(cursor, archetype, ability, tier_data)
        elif ability in ability_stats:
            insert_archetype_specific_tiers(cursor, archetype, ability, ability_stats[ability])
        else:
            print(f"❌ No tier data found for {ability} ({archetype})")

conn.commit()
conn.close()
print("✅ Archetype DB created with dual stat support.")
