#!/usr/bin/env python3
"""Clean up old Redshift clusters."""
import boto3
import os
from dotenv import load_dotenv

load_dotenv()

def cleanup_old_clusters():
    redshift = boto3.client('redshift', region_name='us-east-1')
    
    try:
        clusters = redshift.describe_clusters()['Clusters']
        
        # Keep only the most recent available sales-analyst cluster
        sales_clusters = [c for c in clusters if c['ClusterIdentifier'].startswith('sales-analyst-')]
        available_clusters = [c for c in sales_clusters if c['ClusterStatus'] == 'available']
        
        if len(available_clusters) > 1:
            # Sort by creation time, keep the newest
            available_clusters.sort(key=lambda x: x['ClusterCreateTime'], reverse=True)
            clusters_to_delete = available_clusters[1:]  # Delete all except the newest
            
            for cluster in clusters_to_delete:
                cluster_id = cluster['ClusterIdentifier']
                print(f"Deleting cluster: {cluster_id}")
                redshift.delete_cluster(
                    ClusterIdentifier=cluster_id,
                    SkipFinalClusterSnapshot=True
                )
                print(f"✅ Deletion initiated for {cluster_id}")
        
        # Delete incompatible clusters
        incompatible_clusters = [c for c in sales_clusters if c['ClusterStatus'] == 'incompatible-network']
        for cluster in incompatible_clusters:
            cluster_id = cluster['ClusterIdentifier']
            print(f"Deleting incompatible cluster: {cluster_id}")
            redshift.delete_cluster(
                ClusterIdentifier=cluster_id,
                SkipFinalClusterSnapshot=True
            )
            print(f"✅ Deletion initiated for {cluster_id}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    cleanup_old_clusters()