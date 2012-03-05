import sys, csv, argparse, logging, time, json

from bl.vl.kb import KnowledgeBase as KB

LOG_FORMAT = '%(asctime)s|%(levelname)-8s|%(message)s'
LOG_DATEFMT = '%Y-%m-%d %H:%M:%S'
LOG_LEVELS = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']

def make_parser():
    parser = argparse.ArgumentParser(description='update parents')
    parser.add_argument('--logfile', type=str, help='log file (default=stderr)')
    parser.add_argument('--loglevel', type=str, choices=LOG_LEVELS,
                        help='logging level (default=INFO)', default='INFO')
    parser.add_argument('-H', '--host', type=str, help='omero hostname',
                        default='localhost')
    parser.add_argument('-U', '--user', type=str, help='omero user',
                        default='root')
    parser.add_argument('-P', '--passwd', type=str, required=True,
                        help='omero password')
    parser.add_argument('-O', '--operator', type=str, help='operator',
                        required=True)
    parser.add_argument('--in_file', type=str, required=True,
                        help='input file with individual, father and mother')
    return parser

def update_parents(individual, father, mother, operator, kb):
    logger = logging.getLogger()
    check_parents(father, mother, kb)
    backup = {}
    logger.info('Updating parents for individual %s' % (individual.id))
    if individual.father != father:
        backup['father'] = individual.father.id if individual.father else None
        logger.info('Setting father to %s (old value %s)' % (father.id if father else None,
                                                             backup['father']))
        individual.father = father
    if individual.mother != mother:
        backup['mother'] = individual.mother.id if individual.mother else None
        logger.info('Setting mother to %s (old value %s)' % (mother.id if mother else None,
                                                             backup['mother']))
        individual.mother = mother
    if len(backup.items()) > 0:
        update_object(individual, backup, operator, kb)
        return individual
    else:
        logger.warning('No update needed for individual %s' % individual.id)
        return None

def check_parents(father, mother, kb):
    if father and father.gender.enum_label() != kb.Gender.MALE.enum_label():
        raise ValueError('Father (individual %s) gender is %s' % (father.id,
                                                                  father.gender.enum_label()))
    if mother and mother.gender.enum_label() != kb.Gender.FEMALE.enum_label():
        raise ValueError('Mother (individual %s) gender is %s' % (mother.id,
                                                                  mother.gender.enum_label()))

def update_object(obj, backup_values, operator, kb):
    logger = logging.getLogger()
    logger.debug('Building ActionOnAction for object %s' % obj.id)
    act_setup = build_action_setup('update-parents-%f' % time.time(),
                                   backup_values, kb)
    aoa_conf = {
        'setup': act_setup,
        'actionCategory': kb.ActionCategory.UPDATE,
        'operator': operator,
        'target': obj.lastUpdate if obj.lastUpdate else obj.action,
        'context': obj.action.context
        }
    logger.debug('Updating object with new ActionOnAction')
    obj.lastUpdate = kb.factory.create(kb.ActionOnAction, aoa_conf)

def build_action_setup(label, backup, kb):
    logger = logging.getLogger()
    logger.debug('Creating a new ActionSetup with label %s and backup %r' % (label,
                                                                             backup))
    conf = {
        'label' : label,
        'conf' : json.dumps({'backup' : backup})
        }
    asetup = kb.factory.create(kb.ActionSetup, conf)
    return asetup

def main(argv):
    parser = make_parser()
    args = parser.parse_args(argv)

    log_level = getattr(logging, args.loglevel)
    kwargs = {'format': LOG_FORMAT,
              'datefmt': LOG_DATEFMT,
              'level' : log_level}
    if args.logfile:
        kwargs['filename'] = args.logfile
    logging.basicConfig(**kwargs)
    logger = logging.getLogger()

    kb = KB(driver='omero')(args.host, args.user, args.passwd)

    logger.info('Retrieving individuals')
    inds = kb.get_objects(kb.Individual)
    logger.info('Retrieved %d individuals' % len(inds))
    inds_lookup = {}
    for i in inds:
        inds_lookup[i.id] = i

    with open(args.in_file) as in_file:
        to_be_updated = []
        reader = csv.DictReader(in_file, delimiter='\t')
        for row in reader:
            try:
                ind = inds_lookup[row['individual']]
                father = inds_lookup[row['father']] if row['father'] != 'None' else None
                mother = inds_lookup[row['mother']] if row['mother'] != 'None' else None
                ind = update_parents(ind, father, mother, args.operator, kb)
                if ind:
                    to_be_updated.append(ind)
            except KeyError, ke:
                logger.error('Unable to find individual %s' % ke)
            except ValueError, ve:
                logger.error('Unable to update parents for individual %s: %s' % (row['individual'],
                                                                                 ve))
                
    logger.info('%d individuals are going to be updated' % len(to_be_updated))
    kb.save_array(to_be_updated)
    logger.info('Update complete')

if __name__ == '__main__':
    main(sys.argv[1:])
