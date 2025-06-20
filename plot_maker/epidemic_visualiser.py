import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import geopandas as gpd
import matplotlib.dates as mdates
from pathlib import Path
import os

class EpidemicVisualiser:
    """
    A class for creating visualisations from detailed epidemic data with demographic breakdowns.
    """
    def __init__(self, data_path, shp_file_path, current_status_path=None):
        """
        Initialise the visualiser with paths to data file and shapefile
        
        Parameters:
        -----------
        data_path : str
            Path to the detailed demographic summary CSV
        shp_file_path : str
            Path to the MSOA shapefile
        current_status_path : str, optional
            Path to the current status data (if different from data_path)
        """
        print(f"Loading data from {data_path}")
        self.data = pd.read_csv(data_path)
        self.data['timestamp'] = pd.to_datetime(self.data['timestamp'])
        
        # Load current status data if provided, otherwise try to infer path
        if current_status_path:
            self.has_current_status = True
            try:
                print(f"Loading current status data from {current_status_path}")
                self.current_status_data = pd.read_csv(current_status_path)
                self.current_status_data['timestamp'] = pd.to_datetime(self.current_status_data['timestamp'])
            except:
                print(f"ERROR: Could not load current status data from {current_status_path}")
                self.has_current_status = False

        # Check for correct MSOA column name
        if 'super_area' in self.data.columns:
            self.msoa_data_col = 'super_area'
        elif 'msoa' in self.data.columns:
            self.msoa_data_col = 'msoa'
        else:
            # Check for any column that might contain MSOA codes
            possible_cols = [col for col in self.data.columns if 'msoa' in col.lower() or 'area' in col.lower()]
            if possible_cols:
                self.msoa_data_col = possible_cols[0]
                print(f"Using {self.msoa_data_col} as MSOA identifier in data")
            else:
                self.msoa_data_col = None
                print("WARNING: No MSOA column found in data - geographic visualisations won't work")
                
        # Load shapefile
        print(f"Loading shapefile from {shp_file_path}")
        self.geo_data = gpd.read_file(shp_file_path)
        
        # Check the actual column names in the geo_data
        msoa_col = [col for col in self.geo_data.columns if 'MSOA' in col]
        if msoa_col:
            self.msoa_col = msoa_col[0]  # Use the first MSOA column found
            print(f"Using {self.msoa_col} as the MSOA identifier in shapefile")
        else:
            self.msoa_col = 'MSOA11CD'  # Default name
            print(f"No MSOA column found in shapefile, using default name: {self.msoa_col}")
            
        # Set a good style for plots
        sns.set(style="whitegrid")
        plt.rcParams['font.family'] = 'DejaVu Sans'
        
        # Check if data and geo_data share a common identifier
        if self.msoa_data_col:
            print(f"Data '{self.msoa_data_col}' values (sample):\n {self.data[self.msoa_data_col].head()}")
            
            # Get the unique MSOAs in our data to filter the shapefile
            unique_msoas = self.data[self.msoa_data_col].unique()
            print(f"Found {len(unique_msoas)} unique MSOAs in the data")
            
            # Filter the shapefile to only include MSOAs in our data
            self.filtered_geo_data = self.geo_data[self.geo_data[self.msoa_col].isin(unique_msoas)].copy()
            print(f"Filtered shapefile to {len(self.filtered_geo_data)} MSOAs (from {len(self.geo_data)} total)")
        
    def time_series_by_gender(self, metric='infections', figsize=(12, 6), output_path=None):
        """
        Create time series plot of a metric by gender
        
        Parameters:
        -----------
        metric : str
            The metric to visualise ('infections', 'hospitalisations', etc.)
        figsize : tuple
            Figure size
        output_path : str, optional
            If provided, save the figure to this path
        """
        # Aggregate data by timestamp and gender
        gender_data = self.data.groupby(['timestamp', 'gender'])[metric].sum().reset_index()
        
        # Check if we have data
        if len(gender_data) == 0:
            print(f"No data available for {metric} by gender")
            return None
        
        # Create figure
        plt.figure(figsize=figsize)
        
        # Use custom colors for gender
        gender_palette = {"f": "#FF9999", "m": "#9999FF"}
        
        # Create the line plot
        sns.lineplot(
            x='timestamp', 
            y=metric, 
            hue='gender',
            palette=gender_palette,
            linewidth=2.5,
            data=gender_data
        )
        
        # Format the plot
        plt.title(f'{metric.capitalize()} by Gender Over Time', fontsize=16)
        plt.xlabel('Date', fontsize=12)
        plt.ylabel(f'Number of {metric.capitalize()}', fontsize=12)
        plt.xticks(rotation=45)
        plt.grid(True, linestyle='--', alpha=0.7)
        plt.legend(title='Gender', labels=['Female', 'Male'])
        
        # Add annotations for peaks - with error handling
        for gender in gender_data['gender'].unique():
            try:
                gender_subset = gender_data[gender_data['gender'] == gender]
                
                if gender_subset[metric].isnull().all() or len(gender_subset) == 0:
                    continue  # Skip if all values are NaN or empty
                
                # Find the row with maximum value directly
                max_row = gender_subset.loc[gender_subset[metric].idxmax()]
                
                plt.annotate(
                    f'Peak: {max_row[metric]:.0f}',
                    xy=(max_row['timestamp'], max_row[metric]),
                    xytext=(10, 10),
                    textcoords='offset points',
                    arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=.2')
                )
            except Exception as e:
                print(f"Could not annotate peak for gender {gender}: {e}")
        
        plt.tight_layout()
        
        # Save if output path is provided
        if output_path:
            plt.savefig(output_path, dpi=300, bbox_inches='tight')
            print(f"Saved figure to {output_path}")
        
        return plt.gcf()
    
    def time_series_by_age(self, metric='infections', figsize=(14, 8), output_path=None):
        """
        Create time series plot of a metric by age group
        
        Parameters:
        -----------
        metric : str
            The metric to visualise ('infections', 'hospitalisations', etc.)
        figsize : tuple
            Figure size
        output_path : str, optional
            If provided, save the figure to this path
        """
        # Aggregate data by timestamp and age bin
        age_data = self.data.groupby(['timestamp', 'age_bin'])[metric].sum().reset_index()
        
        # Define a function to convert age bins to numeric values for sorting
        def age_to_num(age_bin):
            if age_bin == 'Unknown':
                return 999  # Put at the end
            try:
                return int(age_bin.split('-')[0])
            except:
                return 998  # Put near the end
        
        # Order age bins properly
        unique_bins = sorted(age_data['age_bin'].unique(), key=age_to_num)
        
        # Create figure
        plt.figure(figsize=figsize)
        
        # Create a custom color palette
        palette = sns.color_palette("viridis", len(unique_bins))
        
        # Create the line plot
        ax = sns.lineplot(
            x='timestamp', 
            y=metric, 
            hue='age_bin', 
            hue_order=unique_bins,
            palette=palette,
            linewidth=2,
            data=age_data
        )
        
        # Format the plot
        plt.title(f'{metric.capitalize()} by Age Group Over Time', fontsize=16)
        plt.xlabel('Date', fontsize=12)
        plt.ylabel(f'Number of {metric.capitalize()}', fontsize=12)
        plt.xticks(rotation=45)
        plt.grid(True, linestyle='--', alpha=0.7)
        
        # Move legend outside of plot
        plt.legend(
            title='Age Group', 
            bbox_to_anchor=(1.05, 1), 
            loc='upper left'
        )
        
        plt.tight_layout()
        
        # Save if output path is provided
        if output_path:
            plt.savefig(output_path, dpi=300, bbox_inches='tight')
            print(f"Saved figure to {output_path}")
        
        return plt.gcf()
    
    def heatmap_by_geography(self, metric='infections', date=None, cmap='YlOrRd', figsize=(16, 12), output_path=None, cumulative=False):
        """
        Create geographical heatmap of a specific metric
        
        Parameters:
        -----------
        metric : str
            The metric to visualise ('infections', 'hospitalisations', etc.)
        date : str or datetime
            The specific date to visualise. If None, will use the latest date.
        cmap : str
            Matplotlib colormap name
        figsize : tuple
            Figure size (width, height) in inches. Should be chosen to result in even pixel dimensions.
        output_path : str, optional
            If provided, save the figure to this path
        cumulative : bool
            If True, show cumulative counts up to the date, not just counts for the specific date
        """
        if not self.msoa_data_col:
            print("ERROR: Cannot create geographic heatmap - no MSOA column identified in data")
            return None
            
        if date is None:
            # Use the latest date in the data
            date = self.data['timestamp'].max()
            print(f"Using latest date: {date}")
        
        # Convert to datetime if string
        if isinstance(date, str):
            date = pd.to_datetime(date)
        
        # Filter data for the date (either up to date for cumulative or just the date)
        if cumulative:
            day_data = self.data[self.data['timestamp'] <= date]
            title_prefix = "Cumulative"
        else:
            day_data = self.data[self.data['timestamp'] == date]
            title_prefix = "Daily"
        
        if len(day_data) == 0:
            print(f"No data found for date {date}")
            return None
        
        # Aggregate data by MSOA
        msoa_data = day_data.groupby(self.msoa_data_col)[metric].sum().reset_index()
        msoa_data.columns = [self.msoa_col, metric]  # Ensure column name matches shapefile
        
        print(f"MSOA data shape: {msoa_data.shape}")
        
        # Use the filtered geo_data that only contains MSOAs in our dataset
        geo_data_to_use = self.filtered_geo_data if hasattr(self, 'filtered_geo_data') else self.geo_data
        print(f"Using shapefile with {len(geo_data_to_use)} MSOAs")
        
        # Merge with geographical data
        merged_data = geo_data_to_use.merge(msoa_data, on=self.msoa_col, how='left')
        print(f"Merged data shape: {merged_data.shape}")
        
        # Create the plot - use dimensions that will result in even pixel sizes
        dpi = 150
        fig, ax = plt.subplots(1, 1, figsize=figsize, dpi=dpi)
        
        # Plot the data with a fixed color scale
        max_value = msoa_data[metric].max()
        if max_value > 0:
            norm = plt.Normalize(vmin=0, vmax=max_value * 1.1)  # Leave some headroom
        else:
            norm = None
        
        merged_data.plot(
            column=metric,
            ax=ax,
            cmap=cmap,
            legend=True,
            norm=norm,
            legend_kwds={'label': f"{title_prefix} {metric.capitalize()} on {date.strftime('%Y-%m-%d')}"},
            missing_kwds={'color': 'lightgrey'}
        )
        
        # Add title and formatting
        plt.title(f'{title_prefix} {metric.capitalize()} by MSOA on {date.strftime("%Y-%m-%d")}', fontsize=16)
        plt.axis('off')  # Hide axis
        
        # Save if output path is provided
        if output_path:
            plt.savefig(output_path, dpi=dpi, bbox_inches='tight')
            print(f"Saved figure to {output_path}")
        
        return fig
    
    def stacked_bar_by_age_gender(self, metric='infections', figsize=(14, 10), output_path=None):
        """
        Create stacked bar chart showing distribution by age and gender
        
        Parameters:
        -----------
        metric : str
            The metric to visualise ('infections', 'hospitalisations', etc.)
        figsize : tuple
            Figure size
        output_path : str, optional
            If provided, save the figure to this path
        """
        # Aggregate data by age bin and gender
        agg_data = self.data.groupby(['age_bin', 'gender'])[metric].sum().reset_index()
        
        # Define a function to convert age bins to numeric values for sorting
        def age_to_num(age_bin):
            if age_bin == 'Unknown':
                return 999  # Put at the end
            try:
                return int(age_bin.split('-')[0])
            except:
                return 998  # Put near the end
        
        # Sort the data
        agg_data['age_order'] = agg_data['age_bin'].apply(age_to_num)
        agg_data = agg_data.sort_values('age_order')
        
        # Create the plot
        plt.figure(figsize=figsize)
        
        # Custom colors
        gender_colors = {"f": "#FF9999", "m": "#9999FF"}
        
        # Use a pivot table for easier plotting
        pivot_data = agg_data.pivot(index='age_bin', columns='gender', values=metric)
        pivot_data = pivot_data.reindex(sorted(pivot_data.index, key=age_to_num))
        
        # Plot
        pivot_data.plot(
            kind='bar', 
            stacked=True, 
            color=[gender_colors.get(g, '#AAAAAA') for g in pivot_data.columns]
        )
        
        # Format the plot
        plt.title(f'{metric.capitalize()} by Age Group and Gender', fontsize=16)
        plt.xlabel('Age Group', fontsize=12)
        plt.ylabel(f'Number of {metric.capitalize()}', fontsize=12)
        plt.xticks(rotation=45)
        plt.legend(title='Gender', labels=['Female', 'Male'])
        plt.grid(True, axis='y', linestyle='--', alpha=0.7)
        
        plt.tight_layout()
        
        # Save if output path is provided
        if output_path:
            plt.savefig(output_path, dpi=300, bbox_inches='tight')
            print(f"Saved figure to {output_path}")
        
        return plt.gcf()
    
    def animated_map_over_time(self, metric='infections', output_path='animation.mp4', fps=2, temp_folder=None, cumulative=True):
        """
        Create an animated map showing the progression of the metric over time.
        This version creates individual heatmaps for each date and combines them into an animation.
        
        Parameters:
        -----------
        metric : str
            The metric to visualise
        output_path : str
            Path where to save the animation
        fps : int
            Frames per second for the animation
        temp_folder : str, optional
            Folder to save temporary frame images. If None, creates a folder in the same location as output_path
        cumulative : bool
            If True, show cumulative progression, otherwise show daily values
        """
        if not self.msoa_data_col:
            print("ERROR: Cannot create animated map - no MSOA column identified in data")
            return None
        
        try:
            import os
            import subprocess
            
            # Create temporary directory for frames if not specified
            if temp_folder is None:
                output_dir = os.path.dirname(output_path)
                if not output_dir:
                    output_dir = "."
                temp_folder = os.path.join(output_dir, f"temp_frames_{metric}")
            
            # Ensure the temp folder exists
            os.makedirs(temp_folder, exist_ok=True)
            print(f"Saving frames to {temp_folder}")
            
            # Get all unique dates, ensure they're sorted
            dates = sorted(self.data['timestamp'].unique())
            print(f"Creating animation with {len(dates)} frames")
            
            # Find the maximum value for consistent color scaling
            # For cumulative data, the maximum will be at the last date
            if cumulative:
                # For each MSOA, get the sum of metric across all dates
                max_value = self.data.groupby(self.msoa_data_col)[metric].sum().max()
            else:
                # For daily data, find the maximum daily value
                max_value = self.data.groupby(['timestamp', self.msoa_data_col])[metric].sum().max()
                
            print(f"Maximum {metric} value across all dates: {max_value}")
            
            # Use the filtered geo_data
            geo_data_to_use = self.filtered_geo_data if hasattr(self, 'filtered_geo_data') else self.geo_data
            print(f"Processing frames...")
            # Create frames for each date
            for i, date in enumerate(dates):                
                # Get data up to this date for cumulative, or just this date for daily
                if cumulative:
                    # Filter all data up to and including this date
                    frame_data = self.data[self.data['timestamp'] <= date]
                    title_prefix = "Cumulative"
                else:
                    # Just this date
                    frame_data = self.data[self.data['timestamp'] == date]
                    title_prefix = "Daily"
                
                # Skip if no data for this timeframe
                if len(frame_data) == 0:
                    print(f"  No data for {date}, skipping...")
                    continue
                
                # Aggregate by MSOA
                msoa_data = frame_data.groupby(self.msoa_data_col)[metric].sum().reset_index()
                msoa_data.columns = [self.msoa_col, metric]
                
                # Merge with geo data
                merged_data = geo_data_to_use.merge(msoa_data, on=self.msoa_col, how='left')
                
                # Create the plot - use figsize with even pixel dimensions
                dpi = 150
                # Calculate dimensions that are divisible by 2 when multiplied by DPI
                width_inches = 16  # 16 * 150 = 2400 (even)
                height_inches = 12  # 12 * 150 = 1800 (even)
                fig, ax = plt.subplots(1, 1, figsize=(width_inches, height_inches), dpi=dpi)
                
                # Use consistent color scale across all frames
                if max_value > 0:
                    norm = plt.Normalize(vmin=0, vmax=max_value * 1.1)  # Add 10% headroom
                else:
                    norm = None
                
                # Plot the map
                merged_data.plot(
                    column=metric,
                    ax=ax,
                    cmap='YlOrRd',
                    legend=True,
                    norm=norm,
                    legend_kwds={'label': f"{title_prefix} {metric.capitalize()}"},
                    missing_kwds={'color': 'lightgrey'}
                )
                
                # Add title and date
                date_str = pd.to_datetime(date).strftime("%Y-%m-%d")
                ax.set_title(f'{title_prefix} {metric.capitalize()} by MSOA on {date_str}', fontsize=16)
                
                # Add date indicator in a prominent location
                ax.text(
                    0.5, 0.02, 
                    date_str,
                    transform=ax.transAxes,
                    fontsize=16,
                    ha='center',
                    bbox=dict(facecolor='white', alpha=0.8, boxstyle='round')
                )
                
                ax.axis('off')
                
                # Save frame
                frame_filename = os.path.join(temp_folder, f"frame_{i:04d}.png")
                plt.savefig(frame_filename, dpi=150, bbox_inches='tight')
                plt.close(fig)
            
            # Combine frames into animation using ffmpeg
            frame_pattern = os.path.join(temp_folder, "frame_%04d.png")
            
            # Ensure output directory exists
            output_dir = os.path.dirname(output_path)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir)
            
            # Build ffmpeg command with explicit padding to ensure even dimensions
            ffmpeg_cmd = [
                'ffmpeg', '-y',  # Overwrite output if it exists
                '-framerate', str(fps),
                '-i', frame_pattern,
                '-c:v', 'libx264',
                '-pix_fmt', 'yuv420p',
                '-profile:v', 'high',
                '-crf', '20',  # Quality - lower is better
                # Add padding filter to ensure even dimensions
                '-vf', 'pad=ceil(iw/2)*2:ceil(ih/2)*2,fps=30',
                str(output_path)  # Convert Path to string
            ]
            
            # Run ffmpeg - convert all elements to strings before joining
            print(f"Running ffmpeg command: {' '.join(str(x) for x in ffmpeg_cmd)}")
            result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                print(f"Animation saved to {output_path}")
                return True
            else:
                print(f"Error creating animation with ffmpeg: {result.stderr}")
                # Try one more approach - use a different vf filter
                print("Trying alternative ffmpeg command...")
                
                # Build alternative ffmpeg command with scale filter
                alt_ffmpeg_cmd = [
                    'ffmpeg', '-y',
                    '-framerate', str(fps),
                    '-i', frame_pattern,
                    '-c:v', 'libx264',
                    '-pix_fmt', 'yuv420p',
                    '-profile:v', 'high',
                    '-crf', '20',
                    # Scale to even dimensions instead of padding
                    '-vf', 'scale=trunc(iw/2)*2:trunc(ih/2)*2,fps=30',
                    str(output_path)
                ]
                
                # Run alternative ffmpeg command
                print(f"Running alternative ffmpeg command: {' '.join(str(x) for x in alt_ffmpeg_cmd)}")
                alt_result = subprocess.run(alt_ffmpeg_cmd, capture_output=True, text=True)
                
                if alt_result.returncode == 0:
                    print(f"Animation saved to {output_path} using alternative method")
                    return True
                else:
                    print(f"Error with alternative ffmpeg command: {alt_result.stderr}")
                    # Fall back to matplotlib animation if ffmpeg fails
                    print("Falling back to matplotlib animation...")
                    return self._animated_map_fallback(metric, output_path, fps, cumulative)
                
        except Exception as e:
            print(f"Error creating animation: {e}")
            import traceback
            traceback.print_exc()
            return None
            
    def _animated_map_fallback(self, metric='infections', output_path='animation.mp4', fps=2, cumulative=True):
        """Fallback animation method using matplotlib's FuncAnimation"""
        try:
            # Get all unique dates, ensure they're sorted
            dates = sorted(self.data['timestamp'].unique())
            print(f"Creating fallback animation with {len(dates)} frames")
            
            # Create a figure with even pixel dimensions
            width_inches, height_inches = 16, 12  # Will result in even pixel dimensions
            dpi = 150
            fig, ax = plt.subplots(figsize=(width_inches, height_inches), dpi=dpi)
            
            # Find the maximum value for consistent color scaling
            if cumulative:
                # For cumulative data, max will be at the end
                max_value = self.data.groupby(self.msoa_data_col)[metric].sum().max()
                title_prefix = "Cumulative"
            else:
                # For daily data, find max daily value
                max_value = self.data.groupby(['timestamp', self.msoa_data_col])[metric].sum().max()
                title_prefix = "Daily"
            
            # Use the filtered geo_data
            geo_data_to_use = self.filtered_geo_data if hasattr(self, 'filtered_geo_data') else self.geo_data
            
            # Function to update the map for each frame
            def update(frame):
                ax.clear()
                date = dates[frame]
                
                # Filter data for this date/period
                if cumulative:
                    day_data = self.data[self.data['timestamp'] <= date]
                else:
                    day_data = self.data[self.data['timestamp'] == date]
                
                # Aggregate by MSOA
                msoa_data = day_data.groupby(self.msoa_data_col)[metric].sum().reset_index()
                msoa_data.columns = [self.msoa_col, metric]
                
                # Merge with geo data
                merged_data = geo_data_to_use.merge(msoa_data, on=self.msoa_col, how='left')
                
                # Plot
                merged_data.plot(
                    column=metric,
                    ax=ax,
                    cmap='YlOrRd',
                    legend=True,
                    vmin=0,
                    vmax=max_value * 1.1,
                    legend_kwds={'label': f"{title_prefix} {metric.capitalize()}"},
                    missing_kwds={'color': 'lightgrey'}
                )
                
                date_str = pd.to_datetime(date).strftime("%Y-%m-%d")
                ax.set_title(f'{title_prefix} {metric.capitalize()} by MSOA on {date_str}', fontsize=16)
                ax.axis('off')
                
                # Add date indicator
                ax.text(
                    0.5, 0.02, 
                    date_str,
                    transform=ax.transAxes,
                    fontsize=16,
                    ha='center',
                    bbox=dict(facecolor='white', alpha=0.8, boxstyle='round')
                )
                
                return [ax]
            
            # Create animation
            from matplotlib.animation import FuncAnimation
            anim = FuncAnimation(fig, update, frames=len(dates), blit=True)
            
            # Save animation with a writer that ensures even dimensions
            try:
                from matplotlib.animation import FFMpegWriter
                writer = FFMpegWriter(fps=fps, metadata=dict(artist='Epidemic Visualiser'),
                                     bitrate=3000, extra_args=['-vf', 'scale=trunc(iw/2)*2:trunc(ih/2)*2'])
                anim.save(str(output_path), writer=writer)
            except Exception as e:
                print(f"Error with FFMpegWriter: {e}")
                # Last resort - use a different writer
                try:
                    anim.save(str(output_path), writer='pillow', fps=fps)
                except Exception as e2:
                    print(f"Error with pillow writer: {e2}")
                    # Try to create just a series of images as a last resort
                    print("Creating separate frame images instead of animation...")
                    # Create a directory for the frames
                    frames_dir = os.path.dirname(output_path) + "/frames_" + os.path.basename(output_path).split('.')[0]
                    os.makedirs(frames_dir, exist_ok=True)
                    
                    # Save each frame individually
                    for i, date in enumerate(dates):
                        print(f"Saving frame {i+1}/{len(dates)}")
                        update(i)
                        plt.savefig(f"{frames_dir}/frame_{i:04d}.png", dpi=dpi)
                    
                    print(f"Frames saved to {frames_dir}")
                    return None
                    
            print(f"Fallback animation saved to {output_path}")
            
            return anim
            
        except Exception as e:
            print(f"Error creating fallback animation: {e}")
            import traceback
            traceback.print_exc()
            return None
            
    def combined_metrics_plot(self, figsize=(20, 15), output_path=None):
        """
        Create a combined plot of all metrics over time
        
        Parameters:
        -----------
        figsize : tuple
            Figure size
        output_path : str, optional
            If provided, save the figure to this path
        """
        metrics = ['infections', 'hospitalisations', 'icu_admissions', 'deaths']
        
        # Create a 2x2 grid
        fig, axes = plt.subplots(2, 2, figsize=figsize, sharex=True)
        axes = axes.flatten()
        
        # Custom colors for each metric
        colors = ['#FF9999', '#9999FF', '#99FF99', '#FFCC99']
        
        for i, metric in enumerate(metrics):
            # Aggregate data
            time_data = self.data.groupby('timestamp')[metric].sum().reset_index()
            
            # Plot
            sns.lineplot(
                x='timestamp', 
                y=metric, 
                data=time_data, 
                ax=axes[i], 
                color=colors[i],
                linewidth=2.5
            )
            
            # Format
            axes[i].set_title(f'{metric.capitalize()} Over Time', fontsize=14)
            axes[i].set_xlabel('Date', fontsize=12)
            axes[i].set_ylabel(f'Number of {metric.capitalize()}', fontsize=12)
            axes[i].xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            axes[i].tick_params(axis='x', rotation=45)
            axes[i].grid(True, linestyle='--', alpha=0.7)
            
            # Add 7-day rolling average
            time_data[f'{metric}_rolling'] = time_data[metric].rolling(window=7).mean()
            sns.lineplot(
                x='timestamp', 
                y=f'{metric}_rolling', 
                data=time_data, 
                ax=axes[i], 
                color='black',
                linewidth=1.5,
                linestyle='--',
                label='7-day Avg'
            )
            axes[i].legend()
        
        plt.tight_layout()
        
        # Save if output path is provided
        if output_path:
            plt.savefig(output_path, dpi=300, bbox_inches='tight')
            print(f"Saved figure to {output_path}")
        
        return fig

    def heatmap_current_status(self, metric='infections', date=None, cmap='YlOrRd', figsize=(16, 12), output_path=None):
        """
        Create a heatmap showing the current status by MSOA
        
        Parameters:
        -----------
        metric : str
            The metric to visualise ('infections', 'hospitalisations', 'icu_admissions')
        date : str or datetime
            The date to visualise. If None, will use the latest date.
        cmap : str
            Matplotlib colormap name
        figsize : tuple
            Figure size
        output_path : str, optional
            If provided, save the figure to this path
        """
        if not self.has_current_status:
            print("ERROR: No current status data available")
            return None
            
        if not self.msoa_data_col:
            print("ERROR: Cannot create geographic heatmap - no MSOA column identified in data")
            return None
            
        # Map the metric to the column name in the current status data
        metric_map = {
            'infections': 'current_infections',
            'hospitalisations': 'current_hospitalisations',
            'icu_admissions': 'current_icu'
        }
        
        if metric not in metric_map:
            print(f"ERROR: Metric {metric} not recognised for current status")
            return None
            
        current_metric = metric_map[metric]
            
        if date is None:
            # Use the latest date in the data
            date = self.current_status_data['timestamp'].max()
            print(f"Using latest date: {date}")
        
        # Convert to datetime if string
        if isinstance(date, str):
            date = pd.to_datetime(date)
        
        # Filter data for the specific date
        day_data = self.current_status_data[self.current_status_data['timestamp'] == date]
        
        if len(day_data) == 0:
            print(f"No current status data found for date {date}")
            return None
        
        # Aggregate data by MSOA
        msoa_data = day_data.groupby('msoa')[current_metric].sum().reset_index()
        msoa_data.columns = [self.msoa_col, current_metric]  # Ensure column name matches shapefile
        
        print(f"MSOA current status data shape: {msoa_data.shape}")
        
        # Use the filtered geo_data that only contains MSOAs in our dataset
        geo_data_to_use = self.filtered_geo_data if hasattr(self, 'filtered_geo_data') else self.geo_data
        print(f"Using shapefile with {len(geo_data_to_use)} MSOAs")
        
        # Merge with geographical data
        merged_data = geo_data_to_use.merge(msoa_data, on=self.msoa_col, how='left')
        print(f"Merged data shape: {merged_data.shape}")
        
        # Create the plot
        dpi = 150
        fig, ax = plt.subplots(1, 1, figsize=figsize, dpi=dpi)
        
        # Plot the data with a fixed color scale
        max_value = msoa_data[current_metric].max()
        if max_value > 0:
            norm = plt.Normalize(vmin=0, vmax=max_value * 1.1)  # Leave some headroom
        else:
            norm = None
        
        merged_data.plot(
            column=current_metric,
            ax=ax,
            cmap=cmap,
            legend=True,
            norm=norm,
            legend_kwds={'label': f"Currently {metric.rstrip('s')} on {date.strftime('%Y-%m-%d')}"},
            missing_kwds={'color': 'lightgrey'}
        )
        
        # Add title and formatting
        plt.title(f'Currently {metric.rstrip("s")} by MSOA on {date.strftime("%Y-%m-%d")}', fontsize=16)
        plt.axis('off')  # Hide axis
        
        # Save if output path is provided
        if output_path:
            plt.savefig(output_path, dpi=dpi, bbox_inches='tight')
            print(f"Saved figure to {output_path}")
        
        return fig
        
    def animated_current_status(self, metric='infections', output_path='current_animation.mp4', fps=2, temp_folder=None):
        """
        Create an animated map showing the progression of current status over time
        
        Parameters:
        -----------
        metric : str
            The metric to visualise ('infections', 'hospitalisations', 'icu_admissions')
        output_path : str
            Path where to save the animation
        fps : int
            Frames per second for the animation
        temp_folder : str, optional
            Folder to save temporary frame images
        """
        if not self.has_current_status:
            print("ERROR: No current status data available")
            return None
            
        if not self.msoa_data_col:
            print("ERROR: Cannot create animated map - no MSOA column identified in data")
            return None
            
        # Map the metric to the column name in the current status data
        metric_map = {
            'infections': 'current_infections',
            'hospitalisations': 'current_hospitalisations',
            'icu_admissions': 'current_icu'
        }
        
        if metric not in metric_map:
            print(f"ERROR: Metric {metric} not recognised for current status")
            return None
            
        current_metric = metric_map[metric]
        
        try:
            import os
            import tempfile
            import subprocess
            from pathlib import Path
            
            # Create temporary directory for frames if not specified
            if temp_folder is None:
                output_dir = os.path.dirname(output_path)
                if not output_dir:
                    output_dir = "."
                temp_folder = os.path.join(output_dir, f"temp_current_{metric}")
            
            # Ensure the temp folder exists
            os.makedirs(temp_folder, exist_ok=True)
            print(f"Saving frames to {temp_folder}")
            
            # Get all unique dates, ensure they're sorted
            dates = sorted(self.current_status_data['timestamp'].unique())
            print(f"Creating animation with {len(dates)} frames")
            
            # Find the maximum value for consistent color scaling
            max_value = self.current_status_data.groupby(['timestamp', 'msoa'])[current_metric].sum().max()
            print(f"Maximum current {metric} value across all dates: {max_value}")
            
            # Use the filtered geo_data
            geo_data_to_use = self.filtered_geo_data if hasattr(self, 'filtered_geo_data') else self.geo_data
            
            print(f"Processing frames...")
            # Create frames for each date
            for i, date in enumerate(dates):                
                # Filter data for this date
                day_data = self.current_status_data[self.current_status_data['timestamp'] == date]
                
                if len(day_data) == 0:
                    print(f"  No data for {date}, skipping...")
                    continue
                    
                # Aggregate by MSOA
                msoa_data = day_data.groupby('msoa')[current_metric].sum().reset_index()
                msoa_data.columns = [self.msoa_col, current_metric]
                
                # Merge with geo data
                merged_data = geo_data_to_use.merge(msoa_data, on=self.msoa_col, how='left')
                
                # Create the plot
                dpi = 150
                width_inches, height_inches = 16, 12
                fig, ax = plt.subplots(1, 1, figsize=(width_inches, height_inches), dpi=dpi)
                
                # Use consistent color scale across all frames
                if max_value > 0:
                    norm = plt.Normalize(vmin=0, vmax=max_value * 1.1)  # Add 10% headroom
                else:
                    norm = None
                
                # Plot the map
                merged_data.plot(
                    column=current_metric,
                    ax=ax,
                    cmap='YlOrRd',
                    legend=True,
                    norm=norm,
                    legend_kwds={'label': f"Currently {metric.rstrip('s')}"},
                    missing_kwds={'color': 'lightgrey'}
                )
                
                # Add title and date
                date_str = pd.to_datetime(date).strftime("%Y-%m-%d")
                ax.set_title(f'Currently {metric.rstrip("s")} by MSOA on {date_str}', fontsize=16)
                
                # Add date indicator in a prominent location
                ax.text(
                    0.5, 0.02, 
                    date_str,
                    transform=ax.transAxes,
                    fontsize=16,
                    ha='center',
                    bbox=dict(facecolor='white', alpha=0.8, boxstyle='round')
                )
                
                ax.axis('off')
                
                # Save frame
                frame_filename = os.path.join(temp_folder, f"frame_{i:04d}.png")
                plt.savefig(frame_filename, dpi=dpi, bbox_inches='tight')
                plt.close(fig)
            
            # Combine frames into animation using ffmpeg
            frame_pattern = os.path.join(temp_folder, "frame_%04d.png")
            
            # Ensure output directory exists
            output_dir = os.path.dirname(output_path)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir)
            
            # Build ffmpeg command with scale filter to ensure even dimensions
            ffmpeg_cmd = [
                'ffmpeg', '-y',
                '-framerate', str(fps),
                '-i', frame_pattern,
                '-c:v', 'libx264',
                '-pix_fmt', 'yuv420p',
                '-profile:v', 'high',
                '-crf', '20',
                '-vf', 'scale=trunc(iw/2)*2:trunc(ih/2)*2,fps=30',
                str(output_path)
            ]
            
            # Run ffmpeg
            print(f"Running ffmpeg command: {' '.join(str(x) for x in ffmpeg_cmd)}")
            result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                print(f"Animation saved to {output_path}")
                return True
            else:
                print(f"Error creating animation with ffmpeg: {result.stderr}")
                print("Frames were saved to {temp_folder}, but animation creation failed.")
                return False
                
        except Exception as e:
            print(f"Error creating animation: {e}")
            import traceback
            traceback.print_exc()
            return None
        
def generate_complete_report(data_path, shapefile_path, output_folder, current_status_path=None):
    """
    Generate a complete set of visualisations for epidemic data
    
    Parameters:
    -----------
    data_path : str
        Path to the detailed demographic summary CSV
    shapefile_path : str
        Path to the MSOA shapefile
    output_folder : str
        Folder where to save all visualisations
    current_status_path : str, optional
        Path to the current status data file (if different from inferred path)
    """
    # Create output folder if it doesn't exist
    output_folder = Path(output_folder)
    output_folder.mkdir(parents=True, exist_ok=True)
    
    # Create folders for different types of visualisations
    time_series_folder = output_folder / "time_series"
    maps_folder = output_folder / "maps"
    demographics_folder = output_folder / "demographics"
    animations_folder = output_folder / "animations_cumulative"
    current_status_folder = output_folder / "animations_current_status"
    
    for folder in [time_series_folder, maps_folder, demographics_folder, animations_folder, current_status_folder]:
        folder.mkdir(exist_ok=True)
    
    # Initialise visualiser
    print("\n=== Initialising Epidemic Visualiser ===")
    visualiser = EpidemicVisualiser(data_path, shapefile_path, current_status_path)
    
    # Define metrics to visualise
    metrics = ['infections', 'hospitalisations', 'icu_admissions', 'deaths']
    current_metrics = ['infections', 'hospitalisations', 'icu_admissions']  # Deaths don't have a "current" status
    
    # Generate time series visualisations
    print("\n=== Generating Time Series Visualisations ===")
    for metric in metrics:
        print(f"\nGenerating time series visualisations for {metric}...")
        
        # Time series by gender
        output_path = time_series_folder / f"{metric}_by_gender.png"
        visualiser.time_series_by_gender(metric=metric, output_path=output_path)
        
        # Time series by age
        output_path = time_series_folder / f"{metric}_by_age.png"
        visualiser.time_series_by_age(metric=metric, output_path=output_path)
    
    # Generate combined metrics plot
    output_path = time_series_folder / "all_metrics_trends.png"
    visualiser.combined_metrics_plot(output_path=output_path)
    
    # Generate demographic breakdowns
    print("\n=== Generating Demographic Visualisations ===")
    for metric in metrics:
        print(f"\nGenerating demographic visualisations for {metric}...")
        
        # Stacked bar by age and gender
        output_path = demographics_folder / f"{metric}_by_age_gender.png"
        visualiser.stacked_bar_by_age_gender(metric=metric, output_path=output_path)
    
    # Generate geographic heatmaps - both daily and cumulative
    print("\n=== Generating Geographic Heatmaps ===")
    
    # Create latest maps for all metrics - CUMULATIVE
    for metric in metrics:
        print(f"\nGenerating latest cumulative map for {metric}...")
        output_path = maps_folder / f"{metric}_map_cumulative.png"
        visualiser.heatmap_by_geography(
            metric=metric, 
            output_path=output_path, 
            cumulative=True
        )
    
    # Generate current status maps if data is available
    if hasattr(visualiser, 'has_current_status') and visualiser.has_current_status:
        print("\n=== Generating Current Status Maps ===")
        for metric in current_metrics:
            print(f"\nGenerating current status map for {metric}...")
            output_path = current_status_folder / f"current_{metric}_map.png"
            visualiser.heatmap_current_status(
                metric=metric,
                output_path=output_path
            )
        
        # Generate current status animations
        print("\n=== Generating Current Status Animations ===")
        for metric in current_metrics:
            print(f"\nGenerating current status animation for {metric}...")
            output_path = current_status_folder / f"current_{metric}_animation.mp4"
            temp_folder = current_status_folder / f"temp_current_{metric}"
            visualiser.animated_current_status(
                metric=metric,
                output_path=output_path,
                fps=4,
                temp_folder=temp_folder
            )
    else:
        print("\n=== Skipping Current Status Visualisations - No Data Available ===")
    
    # Create animated maps - CUMULATIVE
    print("\n=== Generating Animated Maps ===")
    for metric in metrics:
        print(f"\nGenerating cumulative animation for {metric}...")
        output_path = animations_folder / f"{metric}_animation_cumulative.mp4"
        # Use a separate temp folder for each animation
        temp_folder = animations_folder / f"temp_{metric}_cumulative"
        visualiser.animated_map_over_time(
            metric=metric, 
            output_path=output_path, 
            fps=4,  # Higher FPS for smoother animation
            temp_folder=temp_folder,
            cumulative=True
        )
        
        # Also create daily animations
        print(f"\nGenerating daily animation for {metric}...")
        output_path = animations_folder / f"{metric}_animation_daily.mp4"
        temp_folder = animations_folder / f"temp_{metric}_daily"
        visualiser.animated_map_over_time(
            metric=metric, 
            output_path=output_path, 
            fps=4,
            temp_folder=temp_folder,
            cumulative=False
        )
    
    print(f"\n=== Report Generation Complete ===")
    print(f"All visualisations saved to {output_folder}")
    print(f"- Time series: {time_series_folder}")
    print(f"- Maps: {maps_folder}")
    print(f"- Demographics: {demographics_folder}")
    print(f"- Animations: {animations_folder}")
    if hasattr(visualiser, 'has_current_status') and visualiser.has_current_status:
        print(f"- Current Status: {current_status_folder}")

if __name__ == "__main__":
    data_path = "results/detailed_demographic_summary.csv"
    shapefile_path = "data/input/geography/MSOA_2011_EW_BFC_V3.shp"
    output_folder = "output_graphs/visualisations"
    current_status_path="results/current_status_by_msoa.csv"

    
    generate_complete_report(data_path, shapefile_path, output_folder, current_status_path)