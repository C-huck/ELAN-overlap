from bs4 import BeautifulSoup
import pandas as pd

def eaf_read(fileName):
  #read in eaf (xml) file
  with open(fineName) as fp:
      xml_doc = fp.read()
  fp.close()

  #parse xml file, create soup
  soup= BeautifulSoup(xml_doc, "lxml-xml")

  #FIND TIME SLOTS
  master_ts = soup.find_all("TIME_SLOT")

  #FIND TIER NAMES   
  a = soup.find_all("TIER")
  tier_names = [s['TIER_ID'] for s in a]
  
  return tier_names,master_ts,soup

def get_start_stop(tier_names,master_ts,soup):    
    time_slots=[]
    annotation_values=[]
    for i in range(len(tier_names)):
        tiers = soup.find_all('TIER',TIER_ID=tier_names[i])
        c = tiers[0].find_all('ANNOTATION')
        start = []
        annote = []
        for j in range(len(c)):
            d = c[j].find_all('ALIGNABLE_ANNOTATION')
            e = [s['TIME_SLOT_REF1'] for s in d][0]
            ee = [s['TIME_SLOT_REF2'] for s in d][0]
            for f in master_ts:
                if f["TIME_SLOT_ID"] == e:
                    g = int(f["TIME_VALUE"])
                if f["TIME_SLOT_ID"] == ee:
                    gg = int(f["TIME_VALUE"])
            start.append([[int(s['TIME_SLOT_REF1'][2:]) for s in d][0],[int(s['TIME_SLOT_REF2'][2:]) for s in d][0],g,gg])
            annote.append(d[0].ANNOTATION_VALUE.string)
        time_slots.append(start)
        annotation_values.append(annote)
    return time_slots, annotation_values

def overlaps(base,ref,time_slots,annotation_values):
    results =[]
    for i,y in enumerate(time_slots[base]):
        for ii,yy in enumerate(time_slots[ref]):
            if y[0] < yy[0] and y[1] > yy[1]: #containment
                results.append([annotation_values[base][i],annotation_values[ref][ii],"contains",yy[1]-yy[0]])
            elif yy[0] < y[0] and yy[1] > y[1]:  #contained-by
                results.append([annotation_values[base][i],annotation_values[ref][ii],"contained by",y[1]-y[0]])
            elif yy[0] > y[0] and y[1] > yy[0] and yy[1] > y[1]:  #right edge contained
                results.append([annotation_values[base][i],annotation_values[ref][ii],"right edge",y[3]-yy[2]])
            elif yy[0] < y[0] and y[0] < yy[1] and yy[1] < y[1]:  #left edge contained
                results.append([annotation_values[base][i],annotation_values[ref][ii],"left edge",yy[3]-y[2]])
    return results

tier_names,master_ts,soup = eaf_read("PoS2.eaf")

time_slots, annotation_values = get_start_stop(tier_names,master_ts,soup)

#view tier names; function 'overlaps' takes tier indices, not names. 
print(tier_names)

#results for tiers 2 (gloss) and 3 (brows)
res_gl_br = pd.DataFrame(data=overlaps(2,3,time_slots,annotation_values),columns=["Annotation Val. 1","Annotation Val. 2","Overlap Type","Duration overlap"])
res_gl_br.head()

#results for tiers 3 (brows) and 5 (Second hand)
res_br_h2 = pd.DataFrame(data=overlaps(3,5,time_slots,annotation_values),columns=["Annotation Val. 1","Annotation Val. 2","Overlap Type","Duration overlap"])
res_br_h2.head()

#Test, for instance, whether brows occur longer with the dominant hand (Gloss tier) or non-dominant hand (Second hand tier)
#raw duration difference
res_gl_br['Duration overlap'].sum() - res_br_h2['Duration overlap'].sum()

#normalized duration difference
(res_gl_br['Duration overlap'].sum()/len(res_gl_br)) - (res_br_h2['Duration overlap'].sum()/len(res_br_h2))



