import json
import matplotlib.pyplot as plt
import os
import numpy as np

# Provided JSON data
data = {
    "total_requests": 500,
    "success_count": 200,
    "failed_count": 300,
    "success_rate": 40.0,
    "failed_rate": 60.0,
    "average_duration_ms": {"success": 12.5324, "failed": 509.757},
    "tool_summary": {
        "add_numbers": {"count": 145, "avg_duration": 12.5032},
        "nonexistent_tool_for_test": {"count": 75, "avg_duration": 12.5159},
        "error_tool": {"count": 75, "avg_duration": 12.4717},
        "delay": {"count": 75, "avg_duration": 2001.53},
        "multiply_numbers": {"count": 70, "avg_duration": 12.5491},
        "save_text": {"count": 60, "avg_duration": 12.5585},
    },
}

# Ensure reports directory exists
output_dir = "reports"
os.makedirs(output_dir, exist_ok=True)

# --- Generate Pie Chart: Success/Fail Rate ---
labels = "Success", "Failed"
sizes = [data["success_count"], data["failed_count"]]
explode = (0, 0.1)  # only "explode" the 2nd slice (i.e. 'Failed')
colors = ["#4CAF50", "#F44336"]  # Green for success, Red for fail

fig1, ax1 = plt.subplots(figsize=(8, 6))
ax1.pie(sizes, explode=explode, labels=labels, autopct="%1.1f%%", shadow=True, startangle=90, colors=colors)
ax1.axis("equal")  # Equal aspect ratio ensures that pie is drawn as a circle.
plt.title("Tỷ lệ Thực thi Thành công vs Thất bại")
pie_chart_path = os.path.join(output_dir, "success_fail_pie.png")
plt.savefig(pie_chart_path)
print(f"Pie chart saved to {pie_chart_path}")
plt.close(fig1)  # Close the figure to free memory

# --- Generate Bar Chart: Average Duration per Tool ---
tool_names = list(data["tool_summary"].keys())
avg_durations = [details["avg_duration"] for details in data["tool_summary"].values()]

fig2, ax2 = plt.subplots(figsize=(12, 7))  # Adjusted figure size for better label display
bars = ax2.bar(tool_names, avg_durations, color="#2196F3")  # Blue color

# Add labels and title
ax2.set_ylabel("Thời gian Trung bình (ms)")
ax2.set_title("Thời gian Xử lý Trung bình theo Tool")
ax2.set_xticks(np.arange(len(tool_names)))  # Ensure ticks are set correctly
ax2.set_xticklabels(tool_names, rotation=45, ha="right")  # Rotate labels for readability

# Add duration values on top of bars
for bar in bars:
    yval = bar.get_height()
    plt.text(
        bar.get_x() + bar.get_width() / 2.0, yval, f"{yval:.2f}", va="bottom", ha="center"
    )  # Use f-string formatting

plt.tight_layout()  # Adjust layout to prevent labels overlapping
bar_chart_path = os.path.join(output_dir, "tool_duration_bar.png")
plt.savefig(bar_chart_path)
print(f"Bar chart saved to {bar_chart_path}")
plt.close(fig2)  # Close the figure
