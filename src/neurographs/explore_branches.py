import networkx as nx
from aind_segmentation_evaluation.graph_routines import graph_to_volume
from tifffile import imsave

def explore_branches(list_of_graphs, shape):
    branch_lengths = []
    for graph in list_of_graphs:
        # Prune short branches
        graph = prune(graph)
        if graph.number_of_nodes() <= 1:
            continue

        # Traverse graph
        leaf_nodes = [i for i in graph.nodes if graph.degree[i] == 1]
        dfs_edges = list(nx.dfs_edges(graph, leaf_nodes[0]))
        flag_junction = False
        path_length = 0
        for (i, j) in dfs_edges:
            # Check for junction
            if graph.degree[i] > 2:
                flag_junction = True
                path_length = 1
            elif flag_junction:
                path_length += 1

            # Check whether to reset
            if graph.degree[j] == 1:
                flag_junction = False
            elif graph.degree[j] > 2 and flag_junction:
                branch_lengths.append(path_length)
    return branch_lengths

def prune_spurious_paths(graph, min_branch_length=5):
    leaf_nodes = [i for i in graph.nodes if graph.degree[i] == 1]
    for leaf in leaf_nodes:
        # Traverse branch from leaf
        queue = [leaf]
        visited = set()
        hit_junction = False
        while len(queue) > 0:
            node = queue.pop(0)
            nbs = list(graph.neighbors(node))
            if len(nbs) > 2:
                hit_junction = True
                break
            else:
                visited.add(node)
                nb = [nb for nb in nbs if nb not in visited]
                queue.extend(nb)

        # Check length of branch
        if hit_junction and len(visited) <= min_branch_length:
            graph.remove_nodes_from(visited)
    return graph

def prune_short_connectors(graph, min_connector_length):
    leaf_nodes = [i for i in graph.nodes if graph.degree[i] == 1]
    dfs_edges = list(nx.dfs_edges(graph, leaf_nodes[0]))
    remove_edges = []
    flag_junction = False
    path_length = 0
    for (i, j) in dfs_edges:
        # Check for junction
        if graph.degree[i] > 2:
            flag_junction = True
            path_length = 1
            cur_branch = {(i, j)}
        elif flag_junction:
            path_length += 1
            cur_branch.add((i, j))

        if graph.degree[i] == 4:
            None
            #remove_edges.append((i,j))
            #print('node {} has degree 4'.format(i))

        # Check whether to reset
        if graph.degree[j] == 1:
            flag_junction = False
            cur_branch = set()
        elif graph.degree[j] > 2 and flag_junction:
            if path_length < min_connector_length:
                remove_edges.extend(cur_branch)
                graph.remove_edges_from(cur_branch)
                cur_branch = set()    
    return remove_edges

def postprocess_prediction(list_of_graphs, min_connector_length=10):
    upd = []
    for graph in list_of_graphs:
        pruned_graph = prune_spurious_paths(graph)
        if pruned_graph.number_of_nodes() > 3:
            remove_edges = prune_short_connectors(pruned_graph, min_connector_length)
            graph.remove_edges_from(remove_edges)
            for g in nx.connected_components(graph):
                subgraph = graph.subgraph(g).copy()
                if subgraph.number_of_nodes() > 10:
                    upd.append(subgraph)
    return upd

def break_crossovers(list_of_graphs, depth=10):
    crossover_nodes = []
    upd = []
    for i, graph in enumerate(list_of_graphs):
        prune_nodes = detect_crossovers(graph, depth)
        graph.remove_nodes_from(prune_nodes)
        for g in nx.connected_components(graph):
            subgraph = graph.subgraph(g).copy()
            if subgraph.number_of_nodes() > 10:
                upd.append(subgraph)
    return upd

def detect_crossovers(graph, depth):
    cnt = 0
    prune_nodes = []
    junctions = [i for i in graph.nodes() if graph.degree(i) > 2]
    for j in junctions:
        # Explore node
        upd = False
        tree, leafs = count_branches(graph, j, depth)
        num_leafs = len(leafs)

        # Detect crossover
        if num_leafs > 3:
            cnt += 1
            upd = True
            for d in range(1, depth):
                tree_d, leafs_d = count_branches(graph, j, d)
                if len(leafs_d) == num_leafs:
                    prune_nodes.extend(tree_d.nodes())
                    upd = False
                    break
            if upd:
                prune_nodes.extend(tree.nodes())
    return prune_nodes

def count_branches(graph, source, depth):
    tree = nx.dfs_tree(graph, source=source, depth_limit=depth)
    leafs = [i for i in tree.nodes() if tree.degree(i) == 1]
    return tree, leafs