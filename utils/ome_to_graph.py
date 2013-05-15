# Dumps OMERO.biobank data to the persistent graph engine
# (this script is useless when your graph engine is "pygraph")

import sys
import argparse
import logging

from bl.vl.kb import KnowledgeBase as KB

LOG_LEVELS = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']


class GraphDumper(object):
    def __init__(self, kb, logger):
        self.kb = kb
        self.logger = logger
        self.node_classes = [
            kb.Individual,
            kb.Vessel,
            kb.DataSample,
            kb.VLCollection,
            kb.DataCollectionItem,
            kb.LaneSlot,
        ]
        self.relationship_classes = {
            kb.DataCollectionItem: 'dataSample',
            kb.VesselsCollectionItem: 'vessel',
        }

    def __get_nodes__(self):
        nodes = []
        for nc in self.node_classes:
            self.logger.info('Loading %s objects and subclasses' % nc.__name__)
            objs = self.kb.get_objects(nc)
            self.logger.info('Loaded %d objects' % len(objs))
            nodes.extend(objs)
        return nodes

    def __get_edges__(self, nodes):
        edges = []
        self.logger.info('Loading actions')
        acts = self.kb.get_objects(self.kb.Action)
        self.logger.info('Loaded %d actions' % len(acts))
        self.logger.info('Building edges data')
        for n in nodes:
            if hasattr(n.action, 'target'):
                act = n.action
                if type(act.target) in self.relationship_classes:
                    src = getattr(act.target, self.relationship_classes[type(act.target)])
                else:
                    src = act.target
                edges.append({'action': act, 'source': src, 'target': n})
        return edges

    def __save_node__(self, node):
        self.logger.debug('NODE --> %s::%s' % (type(node), node.id))
        self.kb.dt.create_node(node)

    def save_nodes(self):
        nodes = self.__get_nodes__()
        self.logger.info('Saving %d nodes' % len(nodes))
        for n in nodes:
            self.__save_node__(n)
        self.logger.info('Done saving nodes')
        return nodes

    def __save_edge__(self, action, source, destination):
        self.logger.debug('EDGE --> action %s::%s  source %s::%s  target %s::%s' %
                          (type(action), action.omero_id,
                          type(source), source.id,
                          type(destination), destination.id)
        )
        self.kb.dt.create_edge(action, source, destination)

    def save_edges(self, nodes):
        edges = self.__get_edges__(nodes)
        self.logger.info('Saving %d edges' % len(edges))
        for e in edges:
            self.__save_edge__(e['action'], e['source'], e['target'])
        self.logger.info('Done saving edges')


def make_logger(level='INFO', logfile=None):
    log_formatter = logging.Formatter(
        fmt='%(asctime)s|%(levelname)-8s|%(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
    )
    logger = logging.getLogger(__name__)
    for h in logger.handlers:
        logger.removeHandler(h)
    if logfile:
        handler = logging.FileHandler(logfile, 'w')
    else:
        handler = logging.StreamHandler()
    handler.setFormatter(log_formatter)
    logger.addHandler(handler)
    logger.setLevel(getattr(logging, level))
    return logger


def make_parser():
    parser = argparse.ArgumentParser(description='Load existing data from an OMERO server and dump to its graph engine')
    parser.add_argument('--logfile', type=str, help='log file (default=stderr)')
    parser.add_argument('--loglevel', type=str, choices=LOG_LEVELS,
                        help='logging_level', default='INFO')
    parser.add_argument('-H', '--host', type=str, help='omero hostname',
                        required=True)
    parser.add_argument('-U', '--user', type=str, help='omero user',
                        required=True)
    parser.add_argument('-P', '--passwd', type=str, help='omero password',
                        required=True)
    return parser


def main(argv):
    parser = make_parser()
    args = parser.parse_args()

    logger = make_logger(args.loglevel, args.logfile)

    kb = KB(driver='omero')(args.host, args.user, args.passwd)

    dumper = GraphDumper(kb, logger)
    nodes = dumper.save_nodes()
    dumper.save_edges(nodes)

if __name__ == '__main__':
    main(sys.argv[1:])