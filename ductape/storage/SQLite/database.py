#!/usr/bin/env python
"""
Database

Storage library

SQLite Database wrappers
"""
from Bio import SeqIO
from ductape.storage.SQLite.dbstrings import dbcreate, dbboost
from ductape.common.utils import get_span
import logging
import sqlite3
import time

__author__ = "Marco Galardini"

################################################################################
# Log setup

logger = logging.getLogger('ductape.database')

################################################################################
# Classes

class Row(object):
    '''
    Class Row
    Holds all the columns as attributes
    Just provide the single row and its description
    '''
    def __init__(self, data, description):
        for field in description:
            self.__setattr__(field[0],data[description.index(field)])

class DBBase(object):
    '''
    Class DB
    General DB handler 
    '''
    def __init__(self, dbname='storage'):
        self.dbname = dbname
        self.connection = None
        self.cursor = None
        self.connect()
    
    def connect(self):
        self.connection = sqlite3.connect(self.dbname)
        
    def getCursor(self):
        if not self.connection:
            self.connect()
        if not self.cursor:
            self.cursor = self.connection.cursor()
    
    def close(self):
        if self.cursor:
            self.cursor.close()
        self.cursor = None
        if self.connection:
            self.connection.close()
        self.connection = None
        
    def create(self):
        '''
        DB creation
        Returns True/False
        '''
        try:
            with self.connection:
                for command in dbcreate.split(';'):
                    self.connection.execute(command+';')
        except sqlite3.Error, e:
            logger.error('Could not create the database!')
            logger.error(e)
            return False

        return True
    
    def boost(self):
        '''
        The current connection is boosted
        '''
        with self.connection as conn:
            conn.execute(dbboost)
    
class Project(DBBase):
    '''
    Class Project
    Handles projects data
    '''
    def __init__(self, dbname='storage'):
        DBBase.__init__(self, dbname)
        
        self.name = None
        self.description = None
        self.kind = None
        self.tmp = None
        self.creation = None
        self.last = None
        self.genome = None
        self.phenome = None
        self.pangenome = None
    
    def __str__(self):
        self.getProject()
        return ' - '.join([
                 str(self.name),
                 str(self.description),
                 str(self.kind),
                 str(self.creation),
                 str(self.last)
                          ])
    
    def isProject(self):
        '''
        Do we have already a project in there?
        '''
        self.getProject()
        if self.name:
            return True
        else:
            return False
    
    def getProject(self):
        '''
        Grep the project informations from the DB
        '''
        # Get the first row (the only one that makes sense)
        with self.connection as conn:
            cursor = conn.execute('select * from project limit 1;')
        
        data = cursor.fetchall()
        if len(data) == 0:
            return
        for field in cursor.description:
            self.__setattr__(field[0],data[0][cursor.description.index(field)])
            
    def addProject(self, name='Project',
                         description='Generic project',
                         kind='generic', tmp=None):
        '''
        If there is no project it is added to db,
        otherwise an exception is thrown
        '''
        if self.isProject():
            logger.warning('Tried to add a project when one is already defined')
            raise Exception('Only one project at a time!')
        
        creation = time.asctime()
        last = time.asctime()
        
        with self.connection as conn:
            conn.execute('''insert into project (`name`, `description`, `kind`,
                                                `tmp`, `creation`, `last`)
                            values (?,?,?,?,?,?);''',
                         (name, description, kind, tmp, creation, last,))
        
    def updateLast(self):
        '''
        Update the last touch timestamp
        '''
        self.getProject()
        with self.connection as conn:
            conn.execute('update project set last = ? where name = ?;',
                         [time.asctime(),self.name,])
        self.getProject()
    
    def setName(self,newName):
        self.getProject()
        with self.connection as conn:
            conn.execute('update project set name = ? where name = ?;',
                         [newName,self.name,])
        # Update the project
        self.getProject()
        
    def setKind(self,newKind):
        self.getProject()
        with self.connection as conn:
            conn.execute('update project set kind = ? where name = ?;',
                         [newKind,self.name,])
        # Update the project
        self.getProject()
    
    def setGenome(self, status):
        '''
        Set the genomic status of the project
        '''
        self.getProject()
        with self.connection as conn:
            conn.execute('update project set genome = ? where name = ?;',
                         [status,self.name,])
        # Update the project
        self.getProject()
    
    def setPhenome(self, status):
        '''
        Set the phenomic status of the project
        '''
        self.getProject()
        with self.connection as conn:
            conn.execute('update project set phenome = ? where name = ?;',
                         [status,self.name,])
        # Update the project
        self.getProject()
        
    def donePanGenome(self):
        '''
        Update the project informing that the pangenome has been done
        '''
        self.getProject()
        with self.connection as conn:
            conn.execute('update project set pangenome = 1 where name = ?;',
                         [self.name,])
        # Update the project
        self.getProject()
        
    def clearPanGenome(self):
        '''
        Update the project informing that the pangenome has been cleared
        '''
        self.getProject()
        with self.connection as conn:
            conn.execute('update project set pangenome = 0 where name = ?;',
                         [self.name,])
        # Update the project
        self.getProject()
        
    def isPanGenome(self):
        '''
        Get the pangenome status
        '''
        self.getProject()
        if self.pangenome == 1:
            return True
        else:
            return False
    
class Organism(DBBase):
    '''
    Class Organism
    Handles the addition and updates on organisms used by the program
    ''' 
    def __init__(self, dbname='storage'):
        DBBase.__init__(self, dbname)
        
    def __len__(self):
        return self.howMany()
    
    def resetProject(self):
        '''
        Reset the project statuses
        '''
        # Reset the project statuses
        oProj = Project(self.dbname)
        oProj.clearPanGenome()
        oProj.setGenome('none')
        oProj.setPhenome('none')
    
    def isOrg(self, org_id):
        '''
        Is this organism already present?
        '''
        with self.connection as conn:
            cursor=conn.execute('select count(*) from organism where org_id=?;',
                                [org_id,])
        return bool(cursor.fetchall()[0][0])
    
    def isMutant(self, org_id):
        '''
        Is this organism a mutant?
        '''
        with self.connection as conn:
            cursor=conn.execute('select mutant from organism where org_id=?;',
                                [org_id,])
        return bool(cursor.fetchall()[0][0])
    
    def getOrgMutants(self, org_id):
        '''
        Get the list of org_id that are mutants of this organism 
        '''
        if not self.isOrg(org_id):
            return
        
        query = '''
                select distinct org_id
                from organism
                where reference = ?
                and mutant = 1;
                '''
        
        with self.connection as conn:
            cursor = conn.execute(query, (org_id,))
        
        for mut in cursor:
            yield mut[0]
            
    def howManyMutants(self):
        '''
        Get the overall number of mutants
        '''
        query = '''
                select distinct org_id
                from organism
                where mutant = 1;
                '''
        
        with self.connection as conn:
            cursor = conn.execute(query)
        
        muts = 0
        for mut in cursor:
            muts += 1
        return muts
    
    def howMany(self):
        '''
        How many organisms are there?
        '''
        with self.connection as conn:
            cursor=conn.execute('select count(*) from organism;')
        return int(cursor.fetchall()[0][0])
    
    def getAll(self):
        '''
        Returns a list of Row objects about all the organisms
        '''
        with self.connection as conn:
            cursor=conn.execute('select * from organism')
            
        for res in cursor:
            yield Row(res, cursor.description)
        
    def getOrg(self, org_id):
        '''
        Get details about one organism
        '''
        if not self.isOrg(org_id):
            return None
        
        with self.connection as conn:
            cursor=conn.execute('select * from organism where org_id=?;',
                                [org_id,])
            
        return Row(cursor.fetchall()[0], cursor.description)
    
    def addOrg(self, org_id, name=None, description=None,
                    orgfile=None, mutant=False, reference=None, mkind='', color=None):
        '''
        Adds a new organism to the db
        Performs some checks on the fields mutant and reference
        If it is a mutant, the reference organism can be null, otherwise
        an exception is raised if it's not present
        '''
        already = self.isOrg(org_id)
        
        mutant = int(mutant)
        if mutant:
            if reference:
                if not self.isOrg(reference):
                    logger.warning('Reference %s is not present yet!'%reference)
                    raise Exception('This reference (%s) is not present yet!'%reference)
        
        with self.connection as conn:
            if not already:
                conn.execute('''insert into organism (`org_id`, `name`,
                                    `description`, `file`, `mutant`, `reference`,
                                    mkind)
                                values (?,?,?,?,?,?,?);''',
                         (org_id, name, description, orgfile, mutant, reference,
                          mkind))
            else:
                conn.execute('''update organism set name = ?,
                                description = ?, mutant = ?, reference = ?,
                                mkind = ? where org_id = ?;''',
                         (name, description, mutant, reference,
                          mkind, org_id))
            
            if color != None:
                conn.execute('''update organism set color = ? where org_id = ?;''',
                         (color, org_id))
        
        if not already:
            # Reset the genomic/phenomic status
            self.setGenomeStatus(org_id, 'none')
            self.setPhenomeStatus(org_id, 'none')
            self.resetProject()
    
    def delAllOrgs(self):
        '''
        Delete all the organsim from the db
        (including all dependent tables)
        '''
        for org in self.getAll():
            self.delOrg(org.org_id)
            
        self.resetProject()
    
    def delOrg(self, org_id, cascade=False):
        '''
        Delete an organism from the db
        If it's a reference to some mutant remove the children only if cascade 
        '''
        if not self.isOrg(org_id):
            return
        
        with self.connection as conn:
            conn.execute('delete from organism where org_id=?;', (org_id,))
        
        if self.howManyMutants(org_id) > 0 and cascade:
            for mut_id in self.getOrgMutants(org_id):
                self.delOrg(mut_id, cascade=True)
        
        oDel = Genome(self.dbname)
        oDel.delProteome(org_id)
        
        oBDel = Biolog(self.dbname)
        oBDel.delOrg(org_id)
        
        self.resetProject()
        
    def setName(self, org_id, newName):
        '''
        Change the name of an organism
        '''
        with self.connection as conn:
            conn.execute('update project set name = ? where org_id = ?;',
                         [newName,org_id,])
            
    def setDescription(self, org_id, newDescr):
        '''
        Change the description of an organism
        '''
        with self.connection as conn:
            conn.execute('update project set description = ? where org_id = ?;',
                         [newDescr,org_id,])
    
    def setFile(self, org_id, newFile):
        '''
        Change the file of an organism
        '''
        with self.connection as conn:
            conn.execute('update project set orgfile = ? where org_id = ?;',
                         [newFile,org_id,])
            
    def setMutant(self, org_id, mutant=1, reference=None):
        '''
        Make this organism no longer a mutant / a mutant: reference can be null
        otherwise an exception is raised if it's not present
        '''
        mutant=int(mutant)
        if reference and mutant:
            if not self.isOrg(reference):
                logger.warning('Reference %s is not present yet!'%reference)
                raise Exception('This reference (%s) is not present yet!'%reference)
        
        with self.connection as conn:
            conn.execute('update organism set mutant = ? where org_id = ?;',
                         [mutant,org_id,])
                         
    def setColor(self, org_id, color):
        '''
        Set the color of this organism (i.e. used for phenomic plots)
        '''
        # Check how many organisms have the same color
        with self.connection as conn:
            cursor=conn.execute('select count(*) from organism where color = ?;',
                        [color,])
        howmany = int(cursor.fetchall()[0][0])
        # We issue just a warning
        if howmany != 0:
            logger.warning('%d organism(s) already use this color (%s)',(howmany, color))
            
        with self.connection as conn:
            conn.execute('update organism set color = ? where org_id = ?;',
                         [color,org_id,])
    
    def resetGenomes(self):
        '''
        Reset each organism genomic status
        '''
        for org in self.getAll():
            self.setGenomeStatus(org.org_id, 'none')
    
    def resetPhenomes(self):
        '''
        Reset each organism phenomic status
        '''
        for org in self.getAll():
            self.setPhenomeStatus(org.org_id, 'none')
    
    def setAllGenomeStatus(self, status):
        '''
        Change the genomic status of all organisms
        '''
        with self.connection as conn:
            conn.execute('update organism set genome = ?;',
                         [status])
    
    def setGenomeStatus(self, org_id, status):
        '''
        Change the genomic status of an organism
        '''
        with self.connection as conn:
            conn.execute('update organism set genome = ? where org_id = ?;',
                         [status,org_id,])
    
    def setAllPhenomeStatus(self, status):
        '''
        Change the genomic status of all organisms
        '''
        with self.connection as conn:
            conn.execute('update organism set phenome = ?;',
                         [status])
    
    def setPhenomeStatus(self, org_id, status):
        '''
        Change the phenomic status of an organism
        '''
        with self.connection as conn:
            conn.execute('update organism set phenome = ? where org_id = ?;',
                         [status,org_id,])
            
class Genome(DBBase):
    '''
    Class Genome
    Handles the addition and updates on Genomic data used by the program
    ''' 
    def __init__(self, dbname='storage'):
        DBBase.__init__(self, dbname)
    
    def resetProject(self):
        '''
        Reset the project Genomic statuses
        '''
        # Reset the project statuses
        oProj = Project(self.dbname)
        oProj.clearPanGenome()
        oProj.setGenome('none')
    
    def updateStatus(self, org_id, status):
        '''
        Update the organism status
        '''
        oOrg = Organism(self.dbname)
        oOrg.setGenomeStatus(org_id, status)
    
    def clearAllGenome(self):
        '''
        Truncate all the tables about the genomic data
        '''
        logger.debug('Clearing genomic data')
        
        with self.connection as conn:
            conn.execute('delete from protein;')
            conn.execute('delete from ortholog;')
            conn.execute('delete from mapko;')
            
        oOrg = Organism(self.dbname)
        oOrg.resetGenomes()
        
        self.resetProject()
    
    def isProt(self, prot_id):
        '''
        Is this protein already present?
        '''
        with self.connection as conn:
            cursor=conn.execute('select count(*) from protein where prot_id=?;',
                                [prot_id,])
        return bool(cursor.fetchall()[0][0])
    
    def areProts(self, prots):
        '''
        Returns False if at least one prot_id is absent
        '''
        with self.connection as conn:
            for prot_id in prots:
                cursor=conn.execute('select count(*) from protein where prot_id=?;',
                                [prot_id,])
                if not bool(cursor.fetchall()[0][0]):
                    logger.warning('Protein %s is not present yet!'%prot_id)
                    return False
        
        return True
    
    def addProteome(self, org_id, pfile):
        '''
        Add a bunch of proteins belonging to org_id (which must be present!)
        The proteins are present in a fasta file, if a particular protein had 
        already been added, no warnings are thrown
        An exception is raised if the org_id is not present in the database
        '''
        # Is the organism present?
        oCheck = Organism(self.dbname)
        if not oCheck.isOrg(org_id):
            logger.warning('Organism %s is not present yet!'%org_id)
            raise Exception('This organism (%s) is not present yet!'%org_id)
        
        self.boost()
        
        i = 0
        with self.connection as conn:
            for s in SeqIO.parse(open(pfile),'fasta'):
                conn.execute('insert or replace into protein values (?,?,?,?);',
                         [s.id,org_id,s.description,str(s.seq),])
                i += 1
        
        logger.debug('Added %d protein to organism %s'%(i,org_id))
        
        self.updateStatus(org_id, 'none')
        oProj = Project(self.dbname)
        oProj.clearPanGenome()
             
    def getProt(self, prot_id):
        '''
        Get a specific protein matching the provided prot_id
        '''
        with self.connection as conn:
            cursor=conn.execute('select * from protein where prot_id = ?;',
                                [prot_id,])
        
        data = cursor.fetchall()
        if len(data) == 0:
            return None
        else:
            return Row(data[0], cursor.description)
        
    def getAllProt(self, org_id):
        '''
        Get all the proteins from a specific organism
        '''
        # Is the organism present?
        oCheck = Organism(self.dbname)
        if not oCheck.isOrg(org_id):
            return
        
        with self.connection as conn:
            cursor=conn.execute('select * from protein where org_id = ?;',
                                [org_id,])
            
        for res in cursor:
            yield Row(res, cursor.description)
            
    def getRecords(self, org_id):
        '''
        Get all the proteins from a specific organism
        As SeqRecords objects
        '''
        from Bio import Alphabet
        from Bio.Seq import Seq
        from Bio.SeqRecord import SeqRecord
        
        for prot in self.getAllProt(org_id):
            yield SeqRecord(Seq(prot.sequence,
                                Alphabet.IUPAC.ExtendedIUPACProtein()),
                            id = prot.prot_id)
    
    def howMany(self, org_id):
        '''
        How many proteins for my organism?
        '''
        with self.connection as conn:
            cursor=conn.execute('''select count(*) from protein
                                    where org_id=?;''',[org_id,])
        return int(cursor.fetchall()[0][0])
    
    def delProteome(self, org_id):
        '''
        Remove all the proteins related to a specific organism
        Also the pangenome and the map2ko will be deleted!
        '''
        prots = [x.prot_id for x in self.getAllProt(org_id)]
        self.delKOs(prots)
        
        with self.connection as conn:
            conn.execute('delete from protein where org_id=?;', (org_id,))
            
        self.delPanGenome()
        
        self.resetProject()
        oProj = Project(self.dbname)
        oProj.clearPanGenome()
            
    def addKOs(self, kos):
        oCheck = Kegg(self.dbname)
        
        self.boost()
        
        for prot_id,ko_id in kos:
            if not self.isProt(prot_id):
                logger.warning('Protein %s is not present yet!'%prot_id)
                raise Exception('This Protein (%s) is not present yet!'%prot_id)
            if not oCheck.isKO('ko:'+ko_id):
                logger.warning('KO %s is not present yet!'%'ko:'+ko_id)
                raise Exception('This KO (%s) is not present yet!'%'ko:'+ko_id)
        
        with self.connection as conn:
            for prot_id,ko_id in kos:
                conn.execute('insert or replace into mapko values (?,?);',
                             [prot_id,'ko:'+ko_id,])
    
    def getKO(self, prot_id):
        with self.connection as conn:
            cursor=conn.execute('select * from mapko where prot_id = ?;',
                                [prot_id,])
        
        data = cursor.fetchall()
        if len(data) == 0:
            return None
        else:
            return Row(data[0], cursor.description)
    
    def delKOs(self, prots):
        with self.connection as conn:
            for prot_id in prots:
                conn.execute('delete from mapko where prot_id=?;', (prot_id,))
                
        self.resetProject()
                    
    def addPanGenome(self, orthologs):
        '''
        Add the provided pangenome to the db
        A check on each protein is performed
        An exception is raised if at least one protein is missing
        '''
        # Check if all the proteins are present
        prots = [prot_id for ps in orthologs.values() for prot_id in ps]
        for prot_id in prots:
            if not self.isProt(prot_id):
                logger.warning('Protein %s is not present yet!'%prot_id)
                raise Exception('This Protein (%s) is not present yet!'%prot_id)
        
        self.boost()
        
        # Go for it!
        i = 0
        with self.connection as conn:
            for group_id in orthologs:
                for prot_id in orthologs[group_id]:
                    conn.execute('insert or replace into ortholog values (?,?);',
                             [group_id,prot_id,])
                i += 1
        
        oProj = Project(self.dbname)
        oProj.donePanGenome()
        
        logger.debug('Added %d orthologous groups'%(i))
    
    def getPanGenome(self):
        '''
        Returns a dictionary group_id --> [prot_id, ...]
        '''
        pangenome = {}
        with self.connection as conn:
            cursor = conn.execute('''select * from ortholog;''')
        
        for res in cursor:
            obj = Row(res, cursor.description)
            if obj.group_id not in pangenome:
                pangenome[obj.group_id] = []
            pangenome[obj.group_id].append(obj.prot_id)
            
        return pangenome
        
    def getPanGenomeOrgs(self):
        '''
        Returns a dictionary group_id --> [org_id, ...]
        '''
        pangenome = {}
        with self.connection as conn:
            cursor = conn.execute('''select distinct o.group_id, org_id
                                    from ortholog o, protein p
                                    where o.prot_id = p.prot_id;''')
        
        for res in cursor:
            obj = Row(res, cursor.description)
            if obj.group_id not in pangenome:
                pangenome[obj.group_id] = []
            pangenome[obj.group_id].append(obj.org_id)
        
        for group in pangenome:
            pangenome[group] = sorted(pangenome[group])
            
        return pangenome
        
    def alterPanGenome(self):
        # TODO
        raise NotImplementedError
    
    def _getCore(self):
        '''
        Base method to get the core genome
        '''
        # How many organisms are present?
        oCheck = Organism(self.dbname)
        nOrgs = oCheck.howMany()
        
        query = '''
                select distinct group_id, count(distinct org_id) orgs
                from ortholog o, protein r
                where o.prot_id = r.prot_id
                group by group_id
                HAVING orgs = ?;
                '''
        
        with self.connection as conn:
            cursor = conn.execute(query,
                             [nOrgs,])
        
        return cursor
    
    def getCore(self):
        '''
        Returns a list of orthologous groups names belonging to the Core genome
        '''
        cursor = self._getCore()
        
        for res in cursor:
            yield Row(res, cursor.description)
    
    def getLenCore(self):
        '''
        Get core genome size
        '''
        cursor = self._getCore()
        
        i = 0
        for res in cursor:
            i += 1
            
        return i
    
    def _getAcc(self):
        '''
        Base method to get the accessory genome
        '''
        # How many organisms are present?
        oCheck = Organism(self.dbname)
        nOrgs = oCheck.howMany()
        
        query = '''
                select distinct group_id, count(distinct org_id) orgs
                from ortholog o, protein r
                where o.prot_id = r.prot_id
                group by group_id
                HAVING orgs < ?
                and orgs > ?;
                '''
        
        with self.connection as conn:
            cursor = conn.execute(query,
                             [nOrgs,1,])
            
        return cursor
    
    def getAcc(self):
        '''
        Returns a list of orthologous groups names belonging to the Accessory genome
        '''
        cursor = self._getAcc()
        
        for res in cursor:
            yield Row(res, cursor.description)
    
    def getLenAcc(self):
        '''
        Get accessory genome size
        '''
        cursor = self._getAcc()
        
        i = 0
        for res in cursor:
            i += 1
            
        return i
    
    def _getUni(self):
        '''
        Base method to get the unique genome
        '''
        query = '''
                select distinct group_id, count(distinct org_id) orgs
                from ortholog o, protein r
                where o.prot_id = r.prot_id
                group by group_id
                HAVING orgs = ?;
                '''
        
        with self.connection as conn:
            cursor = conn.execute(query,
                             [1,])
        
        return cursor
    
    def getUni(self):
        '''
        Returns a list of orthologous groups names belonging to the Unique genome
        '''
        cursor = self._getUni()
        
        for res in cursor:
            yield Row(res, cursor.description)    
            
    def getLenUni(self):
        '''
        Get unique genome size
        '''
        cursor = self._getUni()
        
        i = 0
        for res in cursor:
            i += 1
            
        return i    
        
    def delPanGenome(self):
        '''
        Remove all the entries about the pangenome
        '''
        with self.connection as conn:
            conn.execute('delete from ortholog')
            
        self.resetProject()
        oProj = Project(self.dbname)
        oProj.clearPanGenome()

class Kegg(DBBase):
    '''
    Class Kegg
    Handles all the data about Kegg entries
    '''
    def __init__(self, dbname='storage'):
        DBBase.__init__(self, dbname)
    
    def addDraftKOs(self, ko):
        '''
        Add new KOs (ignoring errors if they are already present)
        the input is a list, so no details about this KOs are there yet
        '''
        self.boost()
        
        with self.connection as conn:
            for ko_id in ko:
                conn.execute('insert or replace into ko (`ko_id`) values (?);',
                     ('ko:'+ko_id,))
    
    def addKOs(self, ko):
        '''
        Add new KOs (ignoring errors if they are already present)
        the input is a dictionary
        ko_id --> name, description
        '''
        self.boost()
        
        with self.connection as conn:
            for ko_id,values in ko.iteritems():
                name = values[0]
                if len(values) > 1:
                    description = values[1]
                else:
                    description = ''
                conn.execute('insert or replace into ko values (?,?,?,?);',
                     (ko_id,name,description,1,))
    
    def addKOReacts(self, koreact):
        '''
        An exception is thrown if such IDs are not present
        '''
        for ko_id in koreact:
            if not self.isKO(ko_id):
                logger.warning('KO %s is not present yet!'
                                %ko_id)
                raise Exception('This KO (%s) is not present yet!'
                                %ko_id)
            for re_id in koreact[ko_id]:
                if not self.isReaction(re_id):
                    logger.warning('Reaction %s is not present yet!'
                                %re_id)
                    raise Exception('This reaction (%s) is not present yet!'
                                %re_id)
        
        self.boost()
        
        with self.connection as conn:
            for ko_id in koreact:
                for re_id in koreact[ko_id]:
                    conn.execute('insert or ignore into ko_react values (?,?);',
                                 (ko_id,re_id,))
    
    def getKO2Analyze(self):
        '''
        Get all the ko_id to be analyzed
        '''
        with self.connection as conn:
            cursor=conn.execute('select ko_id from ko where analyzed = 0;')
            
        for res in cursor:
            yield Row(res, cursor.description)
            
    def getAllIDs(self):
        '''
        Get all the Kegg IDs already analyzed
        '''
        with self.connection as conn:
            cursor=conn.execute('select ko_id from ko where analyzed = 1;')
            
        for res in cursor:
            yield res[0]
            
        with self.connection as conn:
            cursor=conn.execute('select re_id from reaction;')
            
        for res in cursor:
            yield res[0]
            
        with self.connection as conn:
            cursor=conn.execute('select co_id from compound;')
            
        for res in cursor:
            yield res[0]
    
        with self.connection as conn:
            cursor=conn.execute('select path_id from pathway;')
            
        for res in cursor:
            yield res[0]
            
    def getKO(self, ko_id):
        '''
        Get a specific ko_id
        '''
        if not self.isKO(ko_id):
            return None
        
        with self.connection as conn:
            cursor=conn.execute('select * from ko where ko_id=?;',
                                (ko_id,))
            
        return Row(cursor.fetchall()[0], cursor.description)
    
    def getAllKO(self, org_id):
        '''
        Get all the prot_id, ko_id pair iterator from a specific org_id
        '''
        query = '''
                select distinct m.prot_id, ko_id
                from mapko m, protein p
                where m.prot_id = p.prot_id
                and org_id = ?;
                '''
        
        with self.connection as conn:
            cursor=conn.execute(query,[org_id,])
            
        for res in cursor:
            yield res[0], res[1]
    
    def isKO(self, ko_id):
        '''
        Is this ko_id already present?
        '''
        try:
            with self.connection as conn:
                cursor=conn.execute('select count(*) from ko where ko_id=?;',
                                    (ko_id,))
            return bool(cursor.fetchall()[0][0])
        except Exception, e:
            logger.debug('Got error %s on id %s, assuming id is present'%
                         (str(e),ko_id))
            return True
    
    def addReactions(self, react):
        '''
        Add new reactions (ignoring errors if they are already present)
        the input is a dictionary
        re_id --> name, description
        '''
        self.boost()
        
        with self.connection as conn:
            for re_id, values in react.iteritems():
                name = values[0]
                if len(values) > 1:
                    description = values[1]
                else:
                    description = ''
                conn.execute('insert or ignore into reaction values (?,?,?);',
                     (re_id,name,description,))
    
    def addReactComps(self, reactcomp):
        '''
        An exception is thrown if such IDs are not present
        '''
        for re_id in reactcomp:
            if not self.isReaction(re_id):
                logger.warning('Reaction %s is not present yet!'
                                %re_id)
                raise Exception('This reaction (%s) is not present yet!'
                                %re_id)
            for co_id in reactcomp[re_id]:
                if not self.isCompound(co_id):
                    logger.warning('Compound %s is not present yet!'
                                %co_id)
                    raise Exception('This compound (%s) is not present yet!'
                                %co_id)
        
        self.boost()
        
        with self.connection as conn:
            for re_id in reactcomp:
                for co_id in reactcomp[re_id]:
                    conn.execute('insert or ignore into react_comp values (?,?);',
                                 (re_id,co_id,))
                    
    def addCompReacts(self, compreact):
        '''
        An exception is thrown if such IDs are not present
        '''
        for co_id in compreact:
            if not self.isCompound(co_id):
                logger.warning('Compound %s is not present yet!'
                                %co_id)
                raise Exception('This compound (%s) is not present yet!'
                                %co_id)
            for re_id in compreact[co_id]:
                if not self.isReaction(re_id):
                    logger.warning('Reaction %s is not present yet!'
                                %re_id)
                    raise Exception('This reaction (%s) is not present yet!'
                                %re_id)
        
        self.boost()
        
        with self.connection as conn:
            for co_id in compreact:
                for re_id in compreact[co_id]:
                    conn.execute('insert or ignore into react_comp values (?,?);',
                                 (re_id,co_id,))
    
    def getReaction(self, re_id):
        if not self.isReaction(re_id):
            return None
        
        with self.connection as conn:
            cursor=conn.execute('select * from reaction where re_id=?;',
                                [re_id,])
            
        return Row(cursor.fetchall()[0], cursor.description)
    
    def getAllReactions(self, org_id):
        '''
        Get all the prot_id, re_id pair iterator from a specific org_id
        '''
        query = '''
                select distinct m.prot_id, re_id
                from mapko m, protein p, ko_react r
                where m.prot_id = p.prot_id
                and m.ko_id = r.ko_id
                and org_id = ?;
                '''
        
        with self.connection as conn:
            cursor=conn.execute(query,[org_id,])
            
        for res in cursor:
            yield res[0], res[1]
    
    def isReaction(self, re_id):
        '''
        Is this re_id already present?
        '''
        try:
            with self.connection as conn:
                cursor=conn.execute('select count(*) from reaction where re_id=?;',
                                    (re_id,))
            return bool(cursor.fetchall()[0][0])
        except Exception, e:
            logger.debug('Got error %s on id %s, assuming id is present'%
                         (str(e),re_id))
            return True
        
    def addCompounds(self, co):
        '''
        Add new reactions (ignoring errors if they are already present)
        the input is a dictionary
        co_id --> name, description
        '''
        self.boost()
        
        with self.connection as conn:
            for co_id, values in co.iteritems():
                name = values[0]
                if len(values) > 1:
                    description = values[1]
                else:
                    description = ''
                conn.execute('insert or ignore into compound values (?,?,?);',
                     (co_id,name,description,))
    
    def getCompound(self, co_id):
        if not self.isCompound(co_id):
            return None
        
        with self.connection as conn:
            cursor=conn.execute('select * from compound where co_id=?;',
                                [co_id,])
            
        return Row(cursor.fetchall()[0], cursor.description)
    
    def isCompound(self, co_id):
        '''
        Is this co_id already present?
        '''
        try:
            with self.connection as conn:
                cursor=conn.execute('select count(*) from compound where co_id=?;',
                                    (co_id,))
            return bool(cursor.fetchall()[0][0])
        except Exception, e:
            logger.debug('Got error %s on id %s, assuming id is present'%
                         (str(e),co_id))
            return True
    
    def addPathways(self, path):
        '''
        Add new pathways (ignoring errors if they are already present)
        the input is a dictionary
        path_id --> name, description
        '''
        self.boost()
        
        with self.connection as conn:
            for path_id, values in path.iteritems():
                name = values[0]
                if len(values) > 1:
                    description = values[1]
                else:
                    description = ''
                conn.execute('''insert or replace into pathway
                                (path_id,name,description) values (?,?,?);''',
                     (path_id,name,description,))
    
    def addPathHtml(self, path):
        '''
        Add pathways HTML (ignoring if the pathways are not present)
        the input is a dictionary
        path_id --> html
        '''
        self.boost()
        
        with self.connection as conn:
            for path_id, html in path.iteritems():
                if not html:continue
                html = '\n'.join(html)
                conn.execute('''update pathway set html=? where path_id=?;''',
                     (html,path_id,))
                
    def addPathReacts(self, pathreact):
        '''
        An exception is thrown if such IDs are not present
        '''
        for path_id in pathreact:
            if not self.isPathway(path_id):
                logger.warning('Pathway %s is not present yet!'
                                %path_id)
                raise Exception('This pathway (%s) is not present yet!'
                                %path_id)
            for re_id in pathreact[path_id]:
                if not self.isReaction(re_id):
                    logger.warning('Reaction %s is not present yet!'
                                %re_id)
                    raise Exception('This reaction (%s) is not present yet!'
                                %re_id)
        
        self.boost()
        
        with self.connection as conn:
            for path_id in pathreact:
                for re_id in pathreact[path_id]:
                    conn.execute('insert or ignore into react_path values (?,?);',
                                 (re_id,path_id,))
    
    def getPathReacts(self):
        '''
        Get all the pathway - reaction links
        '''
        query = '''select path_id, re_id
                   from react_path
                   order by path_id'''
        
        with self.connection as conn:
            cursor=conn.execute(query)
            
        for res in cursor:
            yield Row(res, cursor.description)
                    
    def addPathComps(self, pathcomp):
        '''
        An exception is thrown if such IDs are not present
        '''
        for path_id in pathcomp:
            if not self.isPathway(path_id):
                logger.warning('Pathway %s is not present yet!'
                                %path_id)
                raise Exception('This pathway (%s) is not present yet!'
                                %path_id)
            for co_id in pathcomp[path_id]:
                if not self.isCompound(co_id):
                    logger.warning('Compound %s is not present yet!'
                                %co_id)
                    raise Exception('This compound (%s) is not present yet!'
                                %co_id)
        
        self.boost()
        
        with self.connection as conn:
            for path_id in pathcomp:
                for co_id in pathcomp[path_id]:
                    conn.execute('insert or ignore into comp_path values (?,?);',
                                 (co_id,path_id,))
                    
    def addPathMaps(self, pathmap):
        '''
        An exception is thrown if such ID is not present
        '''
        for path_id in pathmap:
            if not self.isPathway(path_id):
                logger.warning('Pathway %s is not present yet!'
                                %path_id)
                raise Exception('This pathway (%s) is not present yet!'
                                %path_id)
        
        self.boost()
        
        with self.connection as conn:
            for path_id in pathmap:
                conn.execute('insert or ignore into pathmap (path_id, html) values (?,?);',
                                 (path_id,'\n'.join(pathmap[path_id]),))
    
    def addPathPics(self, pathpic):
        '''
        An exception is thrown if such ID is not present
        '''
        for path_id in pathpic:
            if not self.isPathway(path_id):
                logger.warning('Pathway %s is not present yet!'
                                %path_id)
                raise Exception('This pathway (%s) is not present yet!'
                                %path_id)
        
        self.boost()
        
        with self.connection as conn:
            for path_id in pathpic:
                pic = open(pathpic[path_id])
                conn.execute('update pathmap set png = ? where path_id = ?;',
                                 (sqlite3.Binary(pic.read()),path_id,))
    
    def getPathway(self, path_id):
        if not self.isPathway(path_id):
            return None
        
        with self.connection as conn:
            cursor=conn.execute('select * from pathway where path_id=?;',
                                [path_id,])
            
        return Row(cursor.fetchall()[0], cursor.description)
    
    def isPathway(self, path_id):
        '''
        Is this path_id already present?
        '''
        try:
            with self.connection as conn:
                cursor=conn.execute('select count(*) from pathway where path_id=?;',
                                    [path_id,])
            return bool(cursor.fetchall()[0][0])
        except Exception, e:
            logger.debug('Got error %s on id %s, assuming id is present'%
                         (str(e),path_id))
            return True
        
    def getCoreReact(self):
        '''
        Get core genome reactions (and numerosity)
        '''
        nOrg = Organism(self.dbname).howMany()
        
        query = '''
                select distinct re_id, count(distinct group_id) num
                from ko_react k, mapko m, ortholog o
                where k.ko_id = m.ko_id
                and o.prot_id = m.prot_id
                and group_id in (select distinct group_id
                                    from ortholog
                                    group by group_id
                                    having count(*) = ?)
                group by re_id
                order by num DESC;
                '''
        
        with self.connection as conn:
            cursor=conn.execute(query,
                                [nOrg,])
            
        for res in cursor:
            yield Row(res, cursor.description)
    
    def getDispensableReact(self):
        '''
        Get dispensable genome reactions (and numerosity)
        '''
        nOrg = Organism(self.dbname).howMany()
        
        query = '''
                select distinct re_id, count(distinct group_id) num
                from ko_react k, mapko m, ortholog o
                where k.ko_id = m.ko_id
                and o.prot_id = m.prot_id
                and group_id in (select distinct group_id
                                    from ortholog
                                    group by group_id
                                    having count(*) < ?)
                group by re_id
                order by num DESC;
                '''
        
        with self.connection as conn:
            cursor=conn.execute(query,
                                [nOrg,])
            
        for res in cursor:
            yield Row(res, cursor.description)
    
    def getAccessoryReact(self):
        '''
        Get accessory genome reactions (and numerosity)
        '''
        nOrg = Organism(self.dbname).howMany()
        
        query = '''
                select distinct re_id, count(distinct group_id) num
                from ko_react k, mapko m, ortholog o
                where k.ko_id = m.ko_id
                and o.prot_id = m.prot_id
                and group_id in (select distinct group_id
                                    from ortholog
                                    group by group_id
                                    having count(*) < ?
                                    and count(*) > 1)
                group by re_id
                order by num DESC;
                '''
        
        with self.connection as conn:
            cursor=conn.execute(query,
                                [nOrg,])
            
        for res in cursor:
            yield Row(res, cursor.description)
    
    def getUniqueReact(self):
        '''
        Get unique genome reactions (and numerosity)
        '''
        query = '''
                select distinct re_id, count(distinct group_id) num
                from ko_react k, mapko m, ortholog o
                where k.ko_id = m.ko_id
                and o.prot_id = m.prot_id
                and group_id in (select distinct group_id
                                    from ortholog
                                    group by group_id
                                    having count(*) = 1)
                group by re_id
                order by num DESC;
                '''
        
        with self.connection as conn:
            cursor=conn.execute(query)
            
        for res in cursor:
            yield Row(res, cursor.description)
            
    def getOrgReact(self, org_id):
        '''
        Get reactions from a defined organism (and numerosity)
        '''
        query = '''
                select distinct re_id, count(distinct p.prot_id) num
                from ko_react k, mapko m, protein p
                where k.ko_id = m.ko_id
                and p.prot_id = m.prot_id
                and org_id = ?
                group by re_id
                order by num DESC;
                '''
        
        with self.connection as conn:
            cursor=conn.execute(query,[org_id,])
            
        for res in cursor:
            yield Row(res, cursor.description)
            
    def getReferenceReact(self, mut_id, ref_id):
        '''
        Get reactions from a reference organism (and numerosity)
        The mutated proteins won't be taken into account
        '''
        query = '''
                select distinct re_id, count(distinct p.prot_id) num
                from ko_react k, mapko m, protein p
                where k.ko_id = m.ko_id
                and p.prot_id = m.prot_id
                and org_id = ?
                and p.prot_id not in (select prot_id
                                    from protein
                                    where org_id = ?)
                group by re_id
                order by num DESC;
                '''
        
        with self.connection as conn:
            cursor=conn.execute(query,[ref_id,mut_id,])
            
        for res in cursor:
            yield Row(res, cursor.description)
            
    def howManyMapped(self, org_id=None, pangenome=''):
        '''
        Returns the number of proteins mapped to kegg
        If no org_id is provided, the mapped proteins from all organism
        is returned
        '''
        
        if pangenome in ['core', 'accessory', 'unique']:
            # How many organisms are present?
            organism = Organism(self.dbname)
            nOrg = organism.howMany()
        
        if org_id:
            query = '''
                select count(distinct  p.prot_id)
                from mapko m, protein p
                where m.prot_id = p.prot_id
                and org_id = ?;
                '''
        elif pangenome == 'core':
            query = '''
                    select count(distinct  o.group_id)
                    from mapko m, ortholog o
                    where m.prot_id = o.prot_id
                    and group_id in (select o.group_id
                                        from ortholog o
                                        group by o.group_id
                                        having count(*) = ?);
                    '''
        elif pangenome == 'accessory':
            query = '''
                    select count(distinct  o.group_id)
                    from mapko m, ortholog o
                    where m.prot_id = o.prot_id
                    and group_id in (select o.group_id
                                        from ortholog o
                                        group by o.group_id
                                        having count(*) > 1 and count(*) < ?);
                    '''
        elif pangenome == 'unique':
            query = '''
                    select count(distinct  o.group_id)
                    from mapko m, ortholog o
                    where m.prot_id = o.prot_id
                    and group_id in (select o.group_id
                                        from ortholog o
                                        group by o.group_id
                                        having count(*) = 1);
                    '''
        else:
            query = '''
                    select count(distinct  m.prot_id)
                    from mapko m;
                    '''
            
        with self.connection as conn:
            if org_id:
                cursor=conn.execute(query,[org_id,])
            elif pangenome in ['core', 'accessory']:
                cursor=conn.execute(query,[nOrg,])
            else:
                cursor=conn.execute(query)
        return int(cursor.fetchall()[0][0])
    
    def howManyKO(self, org_id=None, pangenome=''):
        '''
        Returns the number of KO mapped
        If no org_id is provided, the whole number of KO from all organism
        is returned
        '''
        
        if pangenome in ['core', 'accessory', 'unique']:
            # How many organisms are present?
            organism = Organism(self.dbname)
            nOrg = organism.howMany()
        
        if org_id:
            query = '''
                select count(distinct ko_id)
                from mapko m, protein p
                where m.prot_id = p.prot_id
                and org_id = ?
                '''
        elif pangenome == 'core':
            query = '''
                    select count(distinct ko_id)
                    from mapko m, ortholog o
                    where m.prot_id = o.prot_id
                    and o.group_id in (select o.group_id
                                from ortholog o
                                group by o.group_id
                                having count(*) = ?);
                    '''
        elif pangenome == 'accessory':
            query = '''
                    select count(distinct ko_id)
                    from mapko m, ortholog o
                    where m.prot_id = o.prot_id
                    and o.group_id in (select o.group_id
                                from ortholog o
                                group by o.group_id
                                having count(*) < ? and count(*));
                    '''
        elif pangenome == 'unique':
            query = '''
                    select count(distinct ko_id)
                    from mapko m, ortholog o
                    where m.prot_id = o.prot_id
                    and o.group_id in (select o.group_id
                                from ortholog o
                                group by o.group_id
                                having count(*) = 1);
                    '''
        else:
            query = '''
                    select count(distinct ko_id)
                    from mapko m
                    '''
            
        with self.connection as conn:
            if org_id:
                cursor=conn.execute(query,[org_id,])
            elif pangenome in ['core', 'accessory']:
                cursor=conn.execute(query,[nOrg,])
            else:
                cursor=conn.execute(query)
        return int(cursor.fetchall()[0][0])
    
    def howManyReactions(self, org_id=None, pangenome=''):
        '''
        Returns the number of reactions mapped
        If no org_id is provided, the whole number of reactions from all organism
        is returned
        '''
        
        if pangenome in ['core', 'accessory', 'unique']:
            # How many organisms are present?
            organism = Organism(self.dbname)
            nOrg = organism.howMany()
        
        if org_id:
            query = '''
                select count(k.re_id)
                from mapko m, protein p, ko_react k
                where m.prot_id = p.prot_id
                and org_id = ?
                and m.ko_id = k.ko_id
                '''
        elif pangenome == 'core':
            query = '''
                    select count(*)
                    from (select distinct o.group_id, k.re_id
                        from mapko m, ortholog o, ko_react k
                        where m.prot_id = o.prot_id
                        and m.ko_id = k.ko_id
                        and o.group_id in (select o.group_id
                                    from ortholog o
                                    group by o.group_id
                                    having count(*) = ?));
                    '''
        elif pangenome == 'accessory':
            query = '''
                    select count(*)
                    from (select distinct o.group_id, k.re_id
                        from mapko m, ortholog o, ko_react k
                        where m.prot_id = o.prot_id
                        and m.ko_id = k.ko_id
                        and o.group_id in (select o.group_id
                                    from ortholog o
                                    group by o.group_id
                                    having count(*) < ? and count(*) > 1));
                    '''
        elif pangenome == 'unique':
            query = '''
                    select count(*)
                    from (select distinct o.group_id, k.re_id
                        from mapko m, ortholog o, ko_react k
                        where m.prot_id = o.prot_id
                        and m.ko_id = k.ko_id
                        and o.group_id in (select o.group_id
                                    from ortholog o
                                    group by o.group_id
                                    having count(*) = 1));
                    '''
        else:
            query = '''
                    select count(k.re_id)
                    from mapko m, ko_react k
                    where m.ko_id = k.ko_id
                    '''
            
        with self.connection as conn:
            if org_id:
                cursor=conn.execute(query,[org_id,])
            elif pangenome in ['core', 'accessory']:
                cursor=conn.execute(query,[nOrg,])
            else:
                cursor=conn.execute(query)
        return int(cursor.fetchall()[0][0])
    
    def howManyPathways(self, org_id=None, pangenome=''):
        '''
        Returns the number of pathways mapped
        If no org_id is provided, the whole number of pathways from all organism
        is returned
        '''
        
        if pangenome in ['core', 'accessory', 'unique']:
            # How many organisms are present?
            organism = Organism(self.dbname)
            nOrg = organism.howMany()
        
        if org_id:
            query = '''
                select count(distinct  path_id)
                from mapko m, protein p, ko_react k, react_path r
                where m.prot_id = p.prot_id
                and org_id = ?
                and m.ko_id = k.ko_id
                and k.re_id = r.re_id
                '''
        elif pangenome == 'core':
            query = '''
                    select count(distinct  path_id)
                    from mapko m, ortholog o, ko_react k, react_path r
                    where m.prot_id = o.prot_id
                    and m.ko_id = k.ko_id
                    and k.re_id = r.re_id
                    and o.group_id  in (select o.group_id
                                        from ortholog o
                                        group by o.group_id
                                        having count(*) = ?);
                    '''
        elif pangenome == 'accessory':
            query = '''
                    select count(distinct  path_id)
                    from mapko m, ortholog o, ko_react k, react_path r
                    where m.prot_id = o.prot_id
                    and m.ko_id = k.ko_id
                    and k.re_id = r.re_id
                    and o.group_id  in (select o.group_id
                                        from ortholog o
                                        group by o.group_id
                                        having count(*) < ? and count(*) > 1);
                    '''
        elif pangenome == 'unique':
            query = '''
                    select count(distinct  path_id)
                    from mapko m, ortholog o, ko_react k, react_path r
                    where m.prot_id = o.prot_id
                    and m.ko_id = k.ko_id
                    and k.re_id = r.re_id
                    and o.group_id  in (select o.group_id
                                        from ortholog o
                                        group by o.group_id
                                        having count(*) = 1);
                    '''
        else:
            query = '''
                    select count(distinct  path_id)
                    from mapko m, ko_react k, react_path r
                    where m.ko_id = k.ko_id
                    and k.re_id = r.re_id
                    '''
            
        with self.connection as conn:
            if org_id:
                cursor=conn.execute(query,[org_id,])
            elif pangenome in ['core', 'accessory']:
                cursor=conn.execute(query,[nOrg,])
            else:
                cursor=conn.execute(query)
        return int(cursor.fetchall()[0][0])
    
class Biolog(DBBase):
    '''
    Class Biolog
    Handles all the data about Biolog entries
    '''
    def __init__(self, dbname='storage'):
        DBBase.__init__(self, dbname)
    
    def resetProject(self):
        '''
        Reset the project Phenomic statuses
        '''
        # Reset the project statuses
        oProj = Project(self.dbname)
        oProj.setPhenome('none')
        
    def clearAllPhenome(self):
        '''
        Truncate all the tables about the phenomic data
        '''
        logger.debug('Clearing phenomic data')
        
        with self.connection as conn:
            conn.execute('delete from biolog_exp;')
            conn.execute('delete from biolog_exp_det;')
            conn.execute('delete from biolog_purged_exp;')
            conn.execute('delete from biolog_purged_exp_det;')
            
        oOrg = Organism(self.dbname)
        oOrg.resetPhenomes()
        
        self.resetProject()
    
    def isPlate(self, plate_id):
        '''
        Is this plate present?
        '''
        with self.connection as conn:
            cursor=conn.execute('select count(*) from biolog where plate_id=?;',
                                [plate_id,])
        return bool(cursor.fetchall()[0][0])
    
    def isWell(self, well_id):
        '''
        Is this well present?
        '''
        with self.connection as conn:
            cursor=conn.execute('select count(*) from biolog where well_id=?;',
                                [well_id,])
        return bool(cursor.fetchall()[0][0])
    
    def isZeroSubtracted(self, plate_id, well_id, org_id, replica):
        '''
        Is this particular well zero-subtracted?
        '''
        with self.connection as conn:
            cursor=conn.execute('''select zero from biolog_exp 
                                where plate_id=?
                                and well_id=?
                                and org_id=?
                                and replica=?;''',
                                [plate_id,well_id,org_id,replica,])
            
        return bool(cursor.fetchall()[0][0])
    
    def getPlates(self):
        with self.connection as conn:
            cursor=conn.execute('select distinct plate_id from biolog order by plate_id;')
        
        for res in cursor:
            yield Row(res, cursor.description)
    
    def getPlate(self, plate_id):
        with self.connection as conn:
            cursor=conn.execute('select * from biolog where plate_id=? order by well_id;',
                                [plate_id,])
        
        for res in cursor:
            yield Row(res, cursor.description)
    
    def getWells(self):
        with self.connection as conn:
            cursor=conn.execute('select distinct well_id from biolog order by well_id;')
        
        for res in cursor:
            yield Row(res, cursor.description)
    
    def getWell(self, plate_id, well_id):
        '''
        Get informations on a single well
        '''
        with self.connection as conn:
            cursor=conn.execute('select * from biolog where plate_id=? and well_id=?;',
                                [plate_id,well_id,])
        
        data = cursor.fetchall()
        if len(data) == 0:
            return None
        else:
            return Row(data[0], cursor.description)
        
    def getAllTitles(self):
        '''
        Get the titles for each well
        '''
        with self.connection as conn:
            cursor=conn.execute('''select distinct plate_id, well_id, chemical
                                from biolog;''')
        
        for res in cursor:
            yield Row(res, cursor.description)
    
    def isMulti(self, plate_id, well_id):
        '''
        Returns True if there are other near wells with the same compound
        '''
        with self.connection as conn:
            cursor=conn.execute('''select concentration
                                from biolog
                                where plate_id=? and well_id=?;''',
                                [plate_id,well_id,])
        
        data = cursor.fetchall()
        if len(data) == 0:
            return False
        else:
            return bool(data[0][0])
        
    def getMulti(self, plate_id, well_id):
        '''
        If the desired well is a multiple one, returns all the related wells
        Otherwise it returns None
        '''
        if not self.isMulti(plate_id, well_id):
            return
        
        mywell = self.getWell(plate_id, well_id)
        
        # Which concentration am i?
        with self.connection as conn:
            cursor=conn.execute('''select * from biolog where plate_id=? 
                                and chemical= ? and
                                (concentration=? or concentration=? 
                                or concentration=? or concentration=?);''',
                                [plate_id, mywell.chemical, 1, 2, 3, 4,])
            
        for res in cursor:
            yield Row(res, cursor.description)
    
    def getCategs(self):
        with self.connection as conn:
            cursor=conn.execute('''select distinct category
                                from biolog order by plate_id;''')
        
        for res in cursor:
            yield Row(res, cursor.description)
            
    def getCategByPlate(self, plate_id):
        with self.connection as conn:
            cursor=conn.execute('select category from biolog where plate_id=?;',
                                [plate_id,])
        
        data = cursor.fetchall()
        if len(data) == 0:
            return None
        else:
            return Row(data[0], cursor.description)
        
    def getAllCateg(self, category):
        with self.connection as conn:
            cursor=conn.execute('''select * from biolog where category=?
                                order by plate_id, well_id;''',
                                [category,])
        
        for res in cursor:
            yield Row(res, cursor.description)
    
    def getByCo(self, co_id):
        with self.connection as conn:
            cursor=conn.execute('''select * from biolog where co_id=?
                                order by plate_id, well_id;''',
                                [co_id,])
        
        for res in cursor:
            yield Row(res, cursor.description)
        
    def getCos(self):
        with self.connection as conn:
            cursor=conn.execute('''select distinct co_id from biolog 
                                where co_id is not null
                                order by co_id;''')
        
        for res in cursor:
            yield Row(res, cursor.description)
            
    def getCosByPlate(self, plate_id):
        with self.connection as conn:
            cursor=conn.execute('''select distinct co_id from biolog 
                                where co_id is not null
                                and plate_id=?
                                order by co_id;''',
                                [plate_id,])
        
        for res in cursor:
            yield Row(res, cursor.description)
            
    def getCosByCateg(self, category):
        with self.connection as conn:
            cursor=conn.execute('''select distinct co_id from biolog 
                                where co_id is not null
                                and category=?
                                order by co_id;''',
                                [category,])
        
        for res in cursor:
            yield Row(res, cursor.description)
            
    def getAllCo(self):
        with self.connection as conn:
            cursor=conn.execute('''select * from biolog 
                                where co_id is not null
                                order by plate_id, well_id;''')
        
        for res in cursor:
            yield Row(res, cursor.description)
    
    def addWells(self, explist, clustered=True):
        '''
        Input: a series of Well objects
        If clustered = True, it is assumed that we have generated the 
        activity parameters and calculated the activity index
        Checks are performed
        '''
        query = '''insert or replace into biolog_exp 
                            (plate_id, well_id, org_id, replica, activity, 
                            zero, min, max, height, plateau, slope, lag,
                            area, v, y0, model)
                            values '''
        query1a = '''insert or replace into biolog_exp 
                            (plate_id, well_id, org_id, replica, 
                            zero)
                            values '''
        
        query1 = '''insert or replace into biolog_exp_det
                        (plate_id, well_id, org_id, replica, times, signals)
                        values '''
        
        oCheck = Organism(self.dbname)
        for w in explist:
            if not self.isPlate(w.plate_id):
                logger.warning('Plate %s is not known!'%w.plate_id)
                raise Exception('This plate (%s) is not known!'%w.plate_id)
            if not self.isWell(w.well_id):
                logger.warning('Well %s is not known!'%w.well_id)
                raise Exception('This well (%s) is not known!'%w.well_id)
            if not oCheck.isOrg(w.strain):
                logger.warning('Organism %s is not present yet!'%w.strain)
                raise Exception('This organism (%s) is not present yet!'%w.strain)
            if w.activity is None and clustered:
                logger.warning('Parameters extraction not yet performed!')
                raise Exception('Parameters extraction not yet performed!')
        
        self.boost()
        
        with self.connection as conn:
            if clustered:
                blist = ['''('%s','%s','%s',%s,
                            %s,%s,%s,%s,%s,%s,
                            %s,%s,%s,%s,%s,'%s')'''
                         %(w.plate_id,w.well_id,w.strain,w.replica,
                                  w.activity,int(w.zero),w.min,w.max,w.height,
                                  w.plateau,w.slope,w.lag,w.area,w.v,w.y0,w.model)
                              for w in explist]
            else:
                blist = ['''('%s','%s','%s','%s','%s')'''
                         %(w.plate_id,w.well_id,w.strain,w.replica,int(w.zero))
                         for w in explist]
            
            blist1 = []
            for w in explist:
                blist1 = blist1 + ['''('%s', '%s', '%s', '%s', '%s', '%s')'''
                  %(w.plate_id,w.well_id,w.strain,w.replica,
                   '_'.join([str(x) for x in sorted(w.signals.keys())]),
                   '_'.join([str(w.signals[h]) for h in sorted(w.signals.keys())]))]                
            
            if clustered:
                for bs in get_span(blist, span=1):
                    insert = query + ', '.join(bs)+';'
                    conn.execute(insert)
            else:
                for bs in get_span(blist, span=1):
                    insert = query1a + ', '.join(bs)+';'
                    conn.execute(insert)
                
            conn.execute('''update biolog_exp
                        set model = null where model = '';''')
            
            for bs in get_span(blist1, span=1):
                insert = query1 + ', '.join(bs)+';'
                conn.execute(insert)
    
    def delWells(self, explist):
        '''
        Input: a series of BiologExp objects
        '''
        with self.connection as conn:
            for w in explist:
                conn.execute('''delete from biolog_exp 
                            where plate_id=? and well_id=? and org_id=?
                            and replica=?;''',
                            [w.plate_id,w.well_id,w.org_id,w.replica,])
                
                conn.execute('''delete from biolog_exp_det 
                            where plate_id=? and well_id=? and org_id=?
                            and replica=?;''',
                            [w.plate_id,w.well_id,w.org_id,w.replica,])
                
    def delOrg(self, org_id):
        '''
        Remove all data about a specific organism
        '''
        with self.connection as conn:
            conn.execute('''delete from biolog_exp 
                        where org_id=?;''',
                        [org_id,])
            
            conn.execute('''delete from biolog_exp_det 
                        where org_id=?;''',
                        [org_id,])
            
            conn.execute('''delete from biolog_purged_exp 
                        where org_id=?;''',
                        [org_id,])
            
            conn.execute('''delete from biolog_purged_exp_det 
                        where org_id=?;''',
                        [org_id,])
        
        org = Organism(self.dbname)
        org.setPhenomeStatus(org_id, 'none')
    
    def getWellsByOrg(self, org_id):
        '''
        Get all the wells from a certain organism
        '''
        with self.connection as conn:
            cursor=conn.execute('''select * from biolog_exp  
                        where org_id=?
                        order by replica;''',
                        [org_id,])
        
        for res in cursor:
            yield Row(res, cursor.description)
    
    def getReplicas(self, plate_id, well_id, org_id):
        with self.connection as conn:
            cursor=conn.execute('''select * from biolog_exp  
                        where plate_id=? and well_id=? and org_id=?
                        order by replica;''',
                        [plate_id,well_id,org_id,])
        
        for res in cursor:
            yield Row(res, cursor.description)
    
    def getActiveByPlate(self, plate_id, activity):
        '''
        Get those wells at least active activity
        '''
        with self.connection as conn:
            cursor=conn.execute('''select * from biolog_exp  
                        where plate_id=?
                        and activity>=?;''',
                        [plate_id,activity,])
        
        for res in cursor:
            yield Row(res, cursor.description)
    
    def getAllActive(self, activity):
        '''
        Get those wells at least active activity
        '''
        with self.connection as conn:
            cursor=conn.execute('''select * from biolog_exp  
                        where activity>=?;''',
                        [activity,])
        
        for res in cursor:
            yield Row(res, cursor.description)
    
    def howManyActive(self,activity):
        '''
        How many wells are active at least activity?
        '''
        with self.connection as conn:
            cursor=conn.execute('''select count(*) from biolog_exp
                                    where activity>=?;''',[activity,])
        return int(cursor.fetchall()[0][0])
    
    def howManyActiveByPlate(self, plate_id, activity):
        '''
        How many wells are active at least activity?
        '''
        with self.connection as conn:
            cursor=conn.execute('''select count(*) from biolog_exp
                                    where activity>=?
                                    and plate_id=?;''',[activity,plate_id,])
        return int(cursor.fetchall()[0][0])
    
    def howManyActiveByOrg(self, org_id, activity):
        '''
        How many wells are active at least activity?
        '''
        with self.connection as conn:
            cursor=conn.execute('''select count(*) from biolog_exp
                                    where activity>=?
                                    and org_id=?;''',[activity,org_id,])
        return int(cursor.fetchall()[0][0])
    
    def getAllWells(self):
        '''
        Get all the wells from the storage
        '''
        with self.connection as conn:
            cursor=conn.execute('''select * from biolog_exp;''')
        
        for res in cursor:
            yield Row(res, cursor.description)
    
    def maxSignal(self):
        '''
        Get the maximum signal value
        '''
        with self.connection as conn:
            cursor=conn.execute('select max(max) from biolog_exp;')
        return int(cursor.fetchall()[0][0])
    
    def getAllSignals(self):
        '''
        Get all the signals from the storage
        '''
        with self.connection as conn:
            cursor=conn.execute('''select * from biolog_exp_det;''')
        
        for res in cursor:
            yield Row(res, cursor.description)
    
    def getZeroSubtractableSignals(self):
        '''
        Get all the signals that can be zero-subtracted
        '''
        with self.connection as conn:
            cursor=conn.execute('''select * from biolog_exp where zero = 0;''')
        
        notYet = [Row(res, cursor.description) for res in cursor]
        for well in notYet:
            with self.connection as conn:
                cursor=conn.execute('''select * from biolog_exp_det
                                    where plate_id=? and well_id=? and org_id=?
                                    and replica=?;''',
                                    [well.plate_id,well.well_id,
                                     well.org_id,well.replica,])
            for res in cursor:
                yield Row(res, cursor.description)
                
    def atLeastOneZeroSubtracted(self):
        '''
        Is there at least one well that is zero subtracted?
        '''
        with self.connection as conn:
            cursor=conn.execute('select count(*) from biolog_exp where zero=1;')
        return bool(cursor.fetchall()[0][0])
    
    def atLeastOneParameter(self):
        '''
        Is there at least one well with the parameters already calculated?
        '''
        with self.connection as conn:
            cursor=conn.execute('''select count(*)
                                    from biolog_exp
                                    where activity is not null;''')
        return bool(cursor.fetchall()[0][0])
    
    def atLeastOneNoParameter(self):
        '''
        Is there at least one well with no parameters already calculated?
        '''
        with self.connection as conn:
            cursor=conn.execute('''select count(*)
                                    from biolog_exp
                                    where activity is null;''')
        return bool(cursor.fetchall()[0][0])
    
    def getCompounds2Analyse(self):
        '''
        Get all the biolog compounds ID yet to be anlysed
        '''
        with self.connection as conn:
            cursor=conn.execute('''select distinct co_id from biolog
                                 where co_id is not null
                                 and co_id not in (select co_id
                                                 from compound);''')
            
        for res in cursor:
            yield Row(res, cursor.description)
    
    def atLeastOnePurged(self):
        '''
        Is there at least one well discarded?
        '''
        with self.connection as conn:
            cursor=conn.execute('''select count(*)
                                    from biolog_purged_exp;''')
        return bool(cursor.fetchall()[0][0])
    
    def howManyPurged(self):
        '''
        How many discarded wells?
        '''
        with self.connection as conn:
            cursor=conn.execute('''select count(*)
                                    from biolog_purged_exp;''')
        return int(cursor.fetchall()[0][0])
       
    def moveDiscardedWells(self, wells):
        '''
        Get a list of biolog_ids and move them to the
        "purged wells" zone
        '''
        self.boost()
        
        with self.connection as conn:
            for w in wells:
                cursor = conn.execute('''select * from biolog_exp_det
                                where plate_id=? and well_id=? and org_id=?
                                    and replica=?;''',
                                    [w[0],w[1],w[2],w[3],])
                
                well = Row(cursor.fetchall()[0], cursor.description)
                conn.execute('''insert into biolog_purged_exp_det
                        values (?,?,?,?,?,?);''',[w[0],w[1],w[2],w[3],
                                                  well.times, well.signals])
                conn.execute('''delete from biolog_exp_det
                        where plate_id=? and well_id=? and org_id=?
                        and replica=?;''',
                            [w[0],w[1],w[2],w[3],])
                    
                p, w, o, r = w
                cursor = conn.execute('''select * from biolog_exp
                                where plate_id = ?
                                and well_id = ?
                                and org_id = ?
                                and replica = ?;''',[p,w,o,r,])
                well = Row(cursor.fetchall()[0], cursor.description)
                conn.execute('''insert into biolog_purged_exp
                        values (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?);''',
                        [p,w,o,r,well.activity, well.zero,well.min,
                         well.max,well.height,well.plateau,
                         well.slope,well.lag,well.area,
                         well.v,well.y0,well.model])
                conn.execute('''delete from biolog_exp
                                where plate_id = ?
                                and well_id = ?
                                and org_id = ?
                                and replica = ?;''',[p,w,o,r,])
        
    def restoreDiscardedWells(self, plates=[]):
        '''
        Restore all the discarded wells
        '''
        import copy
        
        self.boost()
        
        restored = 0
        
        with self.connection as conn:
            cursor = conn.execute('''select * from biolog_purged_exp_det;''')
            
            exp_det = copy.deepcopy(cursor.description)
            
            for res in cursor:
                well = Row(res, exp_det)
                
                if len(plates) > 0:
                    if well.plate_id not in plates:
                        logger.debug('Skipping restoring of %s'%well.plate_id)
                        continue
                    
                restored += 1
                
                conn.execute('''insert into biolog_exp_det
                        values (?,?,?,?,?,?);''',[well.plate_id, well.well_id,
                                                  well.org_id, well.replica,
                                                  well.times, well.signals])
                conn.execute('''delete from biolog_purged_exp_det
                        where plate_id=? and well_id=? and org_id=?
                        and replica=?;''',
                            [well.plate_id, well.well_id,
                              well.org_id, well.replica,])
                    
                cursor = conn.execute('''select * from biolog_purged_exp
                                where plate_id = ?
                                and well_id = ?
                                and org_id = ?
                                and replica = ?;''',[well.plate_id, well.well_id,
                                                  well.org_id, well.replica,])
                well = Row(cursor.fetchall()[0], cursor.description)
                conn.execute('''insert into biolog_exp
                        values (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?);''',
                        [well.plate_id, well.well_id,
                         well.org_id, well.replica,
                         well.activity, well.zero,well.min,
                         well.max,well.height,well.plateau,
                         well.slope,well.lag,well.area,
                         well.v,well.y0,well.model])
                conn.execute('''delete from biolog_purged_exp
                                where plate_id = ?
                                and well_id = ?
                                and org_id = ?
                                and replica = ?;''',[well.plate_id, well.well_id,
                                                  well.org_id, well.replica,])
        return restored
