# Error Analysis Report

## Top 5 Most Confused Gesture Pairs
| True Label | Predicted | Count |
|-----------|-----------|-------|
| N | M | 17 |
| M | N | 4 |
| O | D | 4 |
| D | O | 3 |
| E | S | 3 |

## Worst Performing Classes
| Class | F1 Score |
|-------|---------|
| N | 0.9319 |
| M | 0.9347 |
| X | 0.9797 |
| S | 0.9831 |
| R | 0.9831 |

## Possible Reasons for Confusion
- Similar finger positions between certain letters
- Background noise in dataset images  
- Lighting variations affecting landmark detection
- Occlusion of certain fingers in similar poses
