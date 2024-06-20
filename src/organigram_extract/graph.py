from organigram_extract.data import ContentNode


class Node:
    """Graph representation of a ContentNode.
    At the moment more of a type alias for ContentNode"""
    content: ContentNode


class Edge:
    """Edge connecting two Nodes.
    These are calculated using the NodePoints and JunctionPoint"""
    u: Node
    v: Node
